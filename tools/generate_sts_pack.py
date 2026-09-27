#!/usr/bin/env python3
"""Build a portable Slay the Spire Java modding knowledge pack.

The pack is intentionally generated from the user's local JARs.  It stores
signatures and fingerprints, not copies of the game or binary assets.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


SCHEMA = "1.1"
PACK_VERSION = "1.3.0"
AI_MANIFEST_SCHEMA = "1.0"
ROLE_FILES = {
    "base_game": "base_game_api.types.jsonl",
    "modthespire": "modthespire_api.types.jsonl",
    "basemod": "basemod_api.types.jsonl",
    "stslib": "stslib_api.types.jsonl",
    "installed_mods": "installed_mods_api.types.jsonl",
    "third_party": "third_party_api.types.jsonl",
}
FRAMEWORK_JARS = {"ModTheSpire.jar", "BaseMod.jar", "StSLib.jar"}
DEFAULT_API_ROLES = {"base_game", "modthespire", "basemod", "stslib"}
INDEX_IGNORED_ROOTS = {".git", ".hg", ".svn", "__pycache__"}
# Steam Workshop 的 API 分类快照（2026-09-27）；用于在报告中明确列出专用库/框架。
WORKSHOP_API_IDS = {
    "1605060445", "1605833019", "1609158507", "2384072973", "1934902042",
    "3433319964", "3338653921", "2970981743", "3338653644", "2554005913",
    "2798024345", "1685625583", "3537874513", "2545997486", "2788071529",
    "1638308801", "2947433143", "3368820915", "3384855730", "2915571146",
    "3189856464", "1612426481", "3617683629", "3420913574", "3465836194",
    "3356036058", "2769174299", "2448191360", "3334117298", "3133446987",
    "1879864511", "2816293692", "2131373661", "2870621729", "2708878699",
    "2633214568", "3038839709", "3005590935", "2130981996", "2013374906",
    "3020919562",
}
TEXT_SUFFIXES = {
    ".json", ".json5", ".properties", ".txt", ".xml", ".md", ".cfg",
    ".atlas", ".fnt", ".csv", ".yml", ".yaml", ".toml", ".java",
}
ANNOTATION_KEYS = {
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpirePatch;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpirePatch2;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpirePatches;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpirePatches2;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpireInitializer;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpireInstrumentPatch;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpireRawPatch;",
    "Lcom/evacipated/cardcrawl/modthespire/lib/SpireOverride;",
}


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def u1(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def u2(self) -> int:
        value = struct.unpack_from(">H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def u4(self) -> int:
        value = struct.unpack_from(">I", self.data, self.pos)[0]
        self.pos += 4
        return value

    def bytes(self, count: int) -> bytes:
        value = self.data[self.pos:self.pos + count]
        self.pos += count
        return value


def decode_utf8(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def descriptor_type(desc: str, pos: int = 0) -> Tuple[str, int]:
    arrays = 0
    while pos < len(desc) and desc[pos] == "[":
        arrays += 1
        pos += 1
    primitives = {
        "B": "byte", "C": "char", "D": "double", "F": "float",
        "I": "int", "J": "long", "S": "short", "Z": "boolean",
        "V": "void",
    }
    if pos >= len(desc):
        value = "?"
        pos = len(desc)
    elif desc[pos] in primitives:
        value = primitives[desc[pos]]
        pos += 1
    elif desc[pos] == "L":
        end = desc.find(";", pos)
        if end < 0:
            end = len(desc)
        value = desc[pos + 1:end].replace("/", ".")
        value = value.replace("$", "$")
        pos = min(len(desc), end + 1)
    else:
        value = desc[pos]
        pos += 1
    return value + "[]" * arrays, pos


def method_descriptor(desc: str) -> Tuple[List[str], str]:
    if not desc.startswith("("):
        return [], descriptor_type(desc)[0]
    pos = 1
    params: List[str] = []
    while pos < len(desc) and desc[pos] != ")":
        value, pos = descriptor_type(desc, pos)
        params.append(value)
    ret, _ = descriptor_type(desc, pos + 1)
    return params, ret


def access_names(flags: int, kind: str = "member") -> List[str]:
    names = [
        (0x0001, "public"), (0x0002, "private"), (0x0004, "protected"),
        (0x0008, "static"), (0x0010, "final"),
        (0x0020, "synchronized" if kind == "method" else "super"),
        (0x0040, "volatile" if kind == "field" else "bridge"),
        (0x0080, "transient" if kind == "field" else "varargs"),
        (0x0100, "native"), (0x0200, "interface"), (0x0400, "abstract"),
        (0x0800, "strict"), (0x1000, "synthetic"), (0x2000, "annotation"),
        (0x4000, "enum"), (0x8000, "module"),
    ]
    return [name for bit, name in names if flags & bit]


def cp_value(cp: Sequence[Any], index: int) -> Any:
    if not index or index >= len(cp):
        return None
    item = cp[index]
    if item is None:
        return None
    tag = item[0]
    if tag == "Utf8":
        return item[1]
    if tag in {"Integer", "Float", "Long", "Double"}:
        return item[1]
    if tag == "String":
        return cp_value(cp, item[1])
    if tag == "Class":
        return cp_value(cp, item[1])
    if tag == "NameAndType":
        return {"name": cp_value(cp, item[1]), "descriptor": cp_value(cp, item[2])}
    if tag in {"Fieldref", "Methodref", "InterfaceMethodref"}:
        return {"class": cp_value(cp, item[1]), "name_and_type": cp_value(cp, item[2])}
    return repr(item)


def cp_utf8(cp: Sequence[Any], index: int) -> str:
    value = cp_value(cp, index)
    return "" if value is None else str(value)


def cp_class(cp: Sequence[Any], index: int) -> str:
    value = cp_value(cp, index)
    if value is None:
        return ""
    return str(value).replace("/", ".")


JVM_OPCODES = {
    0: "nop", 1: "aconst_null", 2: "iconst_m1", 3: "iconst_0", 4: "iconst_1",
    5: "iconst_2", 6: "iconst_3", 7: "iconst_4", 8: "iconst_5", 9: "lconst_0",
    10: "lconst_1", 11: "fconst_0", 12: "fconst_1", 13: "fconst_2", 14: "dconst_0",
    15: "dconst_1", 16: "bipush", 17: "sipush", 18: "ldc", 19: "ldc_w",
    20: "ldc2_w", 21: "iload", 22: "lload", 23: "fload", 24: "dload", 25: "aload",
    26: "iload_0", 27: "iload_1", 28: "iload_2", 29: "iload_3", 30: "lload_0",
    31: "lload_1", 32: "lload_2", 33: "lload_3", 34: "fload_0", 35: "fload_1",
    36: "fload_2", 37: "fload_3", 38: "dload_0", 39: "dload_1", 40: "dload_2",
    41: "dload_3", 42: "aload_0", 43: "aload_1", 44: "aload_2", 45: "aload_3",
    46: "iaload", 47: "laload", 48: "faload", 49: "daload", 50: "aaload",
    51: "baload", 52: "caload", 53: "saload", 54: "istore", 55: "lstore",
    56: "fstore", 57: "dstore", 58: "astore", 59: "istore_0", 60: "istore_1",
    61: "istore_2", 62: "istore_3", 63: "lstore_0", 64: "lstore_1", 65: "lstore_2",
    66: "lstore_3", 67: "fstore_0", 68: "fstore_1", 69: "fstore_2", 70: "fstore_3",
    71: "dstore_0", 72: "dstore_1", 73: "dstore_2", 74: "dstore_3", 75: "astore_0",
    76: "astore_1", 77: "astore_2", 78: "astore_3", 79: "iastore", 80: "lastore",
    81: "fastore", 82: "dastore", 83: "aastore", 84: "bastore", 85: "castore",
    86: "sastore", 87: "pop", 88: "pop2", 89: "dup", 90: "dup_x1", 91: "dup_x2",
    92: "dup2", 93: "dup2_x1", 94: "dup2_x2", 95: "swap", 96: "iadd", 97: "ladd",
    98: "fadd", 99: "dadd", 100: "isub", 101: "lsub", 102: "fsub", 103: "dsub",
    104: "imul", 105: "lmul", 106: "fmul", 107: "dmul", 108: "idiv", 109: "ldiv",
    110: "fdiv", 111: "ddiv", 112: "irem", 113: "lrem", 114: "frem", 115: "drem",
    116: "ineg", 117: "lneg", 118: "fneg", 119: "dneg", 120: "ishl", 121: "lshl",
    122: "ishr", 123: "lshr", 124: "iushr", 125: "lushr", 126: "iand", 127: "land",
    128: "ior", 129: "lor", 130: "ixor", 131: "lxor", 132: "iinc", 133: "i2l",
    134: "i2f", 135: "i2d", 136: "l2i", 137: "l2f", 138: "l2d", 139: "f2i",
    140: "f2l", 141: "f2d", 142: "d2i", 143: "d2l", 144: "d2f", 145: "i2b",
    146: "i2c", 147: "i2s", 148: "lcmp", 149: "fcmpl", 150: "fcmpg", 151: "dcmpl",
    152: "dcmpg", 153: "ifeq", 154: "ifne", 155: "iflt", 156: "ifge", 157: "ifgt",
    158: "ifle", 159: "if_icmpeq", 160: "if_icmpne", 161: "if_icmplt", 162: "if_icmpge",
    163: "if_icmpgt", 164: "if_icmple", 165: "if_acmpeq", 166: "if_acmpne", 167: "goto",
    168: "jsr", 169: "ret", 170: "tableswitch", 171: "lookupswitch", 172: "ireturn",
    173: "lreturn", 174: "freturn", 175: "dreturn", 176: "areturn", 177: "return",
    178: "getstatic", 179: "putstatic", 180: "getfield", 181: "putfield",
    182: "invokevirtual", 183: "invokespecial", 184: "invokestatic", 185: "invokeinterface",
    186: "invokedynamic", 187: "new", 188: "newarray", 189: "anewarray", 190: "arraylength",
    191: "athrow", 192: "checkcast", 193: "instanceof", 194: "monitorenter",
    195: "monitorexit", 196: "wide", 197: "multianewarray", 198: "ifnull", 199: "ifnonnull",
    200: "goto_w", 201: "jsr_w", 202: "breakpoint", 254: "impdep1", 255: "impdep2",
}
JVM_BRANCH_SHORT = set(range(153, 169)) | {198, 199}
JVM_BRANCH_WIDE = {200, 201}
JVM_CP_U2 = {19, 20, 178, 179, 180, 181, 182, 183, 184, 187, 189, 192, 193}
JVM_LOCAL_U1 = set(range(21, 26)) | set(range(54, 59)) | {169}


def _signed(data: bytes, pos: int, width: int) -> int:
    return int.from_bytes(data[pos:pos + width], "big", signed=True)


def disassemble_bytecode(code: bytes, cp: Sequence[Any]) -> List[Dict[str, Any]]:
    """Decode JVM instructions without copying a JVM class-file library."""
    instructions: List[Dict[str, Any]] = []
    pos = 0
    while pos < len(code):
        start = pos
        opcode = code[pos]
        pos += 1
        mnemonic = JVM_OPCODES.get(opcode, f"opcode_{opcode:02x}")
        item: Dict[str, Any] = {
            "offset": start,
            "opcode": f"0x{opcode:02X}",
            "mnemonic": mnemonic,
        }
        if opcode in JVM_LOCAL_U1:
            item["local_index"] = code[pos] if pos < len(code) else None
            pos += 1
        elif opcode == 16:
            item["value"] = _signed(code, pos, 1)
            pos += 1
        elif opcode == 17:
            item["value"] = _signed(code, pos, 2)
            pos += 2
        elif opcode == 18:
            index = code[pos] if pos < len(code) else 0
            pos += 1
            item["constant_pool_index"] = index
            item["constant_pool_value"] = cp_value(cp, index)
        elif opcode in JVM_CP_U2:
            index = int.from_bytes(code[pos:pos + 2], "big") if pos + 2 <= len(code) else 0
            pos += 2
            item["constant_pool_index"] = index
            item["constant_pool_value"] = cp_value(cp, index)
        elif opcode == 132:
            item["local_index"] = code[pos] if pos < len(code) else None
            item["increment"] = _signed(code, pos + 1, 1)
            pos += 2
        elif opcode in JVM_BRANCH_SHORT:
            delta = _signed(code, pos, 2)
            pos += 2
            item["branch_delta"] = delta
            item["branch_target"] = start + delta
        elif opcode in JVM_BRANCH_WIDE:
            delta = _signed(code, pos, 4)
            pos += 4
            item["branch_delta"] = delta
            item["branch_target"] = start + delta
        elif opcode == 185:
            index = int.from_bytes(code[pos:pos + 2], "big") if pos + 2 <= len(code) else 0
            count = code[pos + 2] if pos + 2 < len(code) else 0
            pos += 4
            item.update({"constant_pool_index": index, "constant_pool_value": cp_value(cp, index), "argument_count": count})
        elif opcode in {186}:
            index = int.from_bytes(code[pos:pos + 2], "big") if pos + 2 <= len(code) else 0
            pos += 4
            item["constant_pool_index"] = index
            item["constant_pool_value"] = cp_value(cp, index)
        elif opcode == 188:
            item["atype"] = code[pos] if pos < len(code) else None
            pos += 1
        elif opcode == 197:
            index = int.from_bytes(code[pos:pos + 2], "big") if pos + 2 <= len(code) else 0
            dimensions = code[pos + 2] if pos + 2 < len(code) else 0
            pos += 3
            item.update({"constant_pool_index": index, "constant_pool_value": cp_value(cp, index), "dimensions": dimensions})
        elif opcode == 196:
            widened_opcode = code[pos] if pos < len(code) else 0
            pos += 1
            item["widened_opcode"] = f"0x{widened_opcode:02X}"
            item["widened_mnemonic"] = JVM_OPCODES.get(widened_opcode, f"opcode_{widened_opcode:02x}")
            item["local_index"] = int.from_bytes(code[pos:pos + 2], "big") if pos + 2 <= len(code) else None
            pos += 2
            if widened_opcode == 132:
                item["increment"] = _signed(code, pos, 2)
                pos += 2
        elif opcode in {170, 171}:
            padding = (4 - (pos % 4)) % 4
            pos += padding
            default_delta = _signed(code, pos, 4)
            pos += 4
            item["padding"] = padding
            item["default_target"] = start + default_delta
            if opcode == 170:
                low = _signed(code, pos, 4)
                high = _signed(code, pos + 4, 4)
                pos += 8
                targets = []
                for index in range(max(0, high - low + 1)):
                    delta = _signed(code, pos, 4)
                    pos += 4
                    targets.append({"match": low + index, "target": start + delta})
                item.update({"low": low, "high": high, "targets": targets})
            else:
                pair_count = _signed(code, pos, 4)
                pos += 4
                pairs = []
                for _ in range(max(0, pair_count)):
                    match = _signed(code, pos, 4)
                    delta = _signed(code, pos + 4, 4)
                    pos += 8
                    pairs.append({"match": match, "target": start + delta})
                item["pairs"] = pairs
        elif opcode in {19, 20}:
            # Handled above; retained as a guard for future opcode-table edits.
            pass
        elif opcode in {21, 22, 23, 24, 25, 54, 55, 56, 57, 58, 169}:
            # Handled above; retained as a guard for future opcode-table edits.
            pass
        elif opcode in {0}:
            pass
        else:
            # All remaining JVM instructions have no operands.
            pass
        item["bytecode_hex"] = code[start:pos].hex().upper()
        instructions.append(item)
    return instructions


def annotation_value(reader: Reader, cp: Sequence[Any]) -> Any:
    tag = chr(reader.u1())
    if tag in "BCDFIJSZs":
        return {"kind": tag, "value": cp_value(cp, reader.u2())}
    if tag == "e":
        return {
            "kind": "enum",
            "type": cp_utf8(cp, reader.u2()),
            "value": cp_utf8(cp, reader.u2()),
        }
    if tag == "c":
        value = cp_utf8(cp, reader.u2())
        return {"kind": "class", "value": descriptor_type(value)[0]}
    if tag == "@":
        return {"kind": "annotation", "value": annotation(reader, cp)}
    if tag == "[":
        count = reader.u2()
        return {"kind": "array", "value": [annotation_value(reader, cp) for _ in range(count)]}
    return {"kind": tag}


def annotation(reader: Reader, cp: Sequence[Any]) -> Dict[str, Any]:
    descriptor = cp_utf8(cp, reader.u2())
    count = reader.u2()
    elements: Dict[str, Any] = {}
    for _ in range(count):
        name = cp_utf8(cp, reader.u2())
        elements[name] = annotation_value(reader, cp)
    return {"type": descriptor, "elements": elements}


def annotations_attribute(raw: bytes, cp: Sequence[Any]) -> List[Dict[str, Any]]:
    reader = Reader(raw)
    return [annotation(reader, cp) for _ in range(reader.u2())]


def parameter_annotations_attribute(raw: bytes, cp: Sequence[Any]) -> List[List[Dict[str, Any]]]:
    reader = Reader(raw)
    result = []
    for _ in range(reader.u1()):
        result.append([annotation(reader, cp) for _ in range(reader.u2())])
    return result


def read_attributes(reader: Reader, cp: Sequence[Any], include_code_bytes: bool = False) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "signature": None,
        "constant_value": None,
        "exceptions": [],
        "parameter_names": [],
        "annotations": [],
        "parameter_annotations": [],
        "code": None,
        "source_file": None,
        "inner_classes": [],
    }
    for _ in range(reader.u2()):
        name = cp_utf8(cp, reader.u2())
        length = reader.u4()
        raw = reader.bytes(length)
        sub = Reader(raw)
        if name == "Signature" and length >= 2:
            result["signature"] = cp_utf8(cp, sub.u2())
        elif name == "ConstantValue" and length >= 2:
            result["constant_value"] = cp_value(cp, sub.u2())
        elif name == "Exceptions" and length >= 2:
            result["exceptions"] = [cp_class(cp, sub.u2()) for _ in range(sub.u2())]
        elif name == "MethodParameters" and length >= 1:
            result["parameter_names"] = []
            for _ in range(sub.u1()):
                index = sub.u2()
                flags = sub.u2()
                result["parameter_names"].append({
                    "name": cp_utf8(cp, index) if index else None,
                    "access": access_names(flags, "member"),
                })
        elif name == "Code" and length >= 12:
            max_stack = sub.u2()
            max_locals = sub.u2()
            code_length = sub.u4()
            code = sub.bytes(code_length)
            result["code"] = {
                "max_stack": max_stack,
                "max_locals": max_locals,
                "length": code_length,
                "sha256": hashlib.sha256(code).hexdigest().upper(),
            }
            if include_code_bytes:
                result["code"]["_bytes"] = code
            if sub.pos + 2 <= len(raw):
                exception_count = sub.u2()
                exceptions = []
                for _ in range(exception_count):
                    exceptions.append({
                        "start_pc": sub.u2(),
                        "end_pc": sub.u2(),
                        "handler_pc": sub.u2(),
                        "catch_type": sub.u2(),
                    })
                if include_code_bytes:
                    result["code"]["exception_table"] = exceptions
                if sub.pos + 2 <= len(raw):
                    nested = sub.u2()
                    for _ in range(nested):
                        if sub.pos + 6 > len(raw):
                            break
                        sub.u2()
                        nested_length = sub.u4()
                        sub.bytes(nested_length)
        elif name in {"RuntimeVisibleAnnotations", "RuntimeInvisibleAnnotations"}:
            result["annotations"].extend(annotations_attribute(raw, cp))
        elif name in {"RuntimeVisibleParameterAnnotations", "RuntimeInvisibleParameterAnnotations"}:
            result["parameter_annotations"].append(parameter_annotations_attribute(raw, cp))
        elif name == "AnnotationDefault":
            result["annotation_default"] = annotation_value(sub, cp)
        elif name == "SourceFile" and length >= 2:
            result["source_file"] = cp_utf8(cp, sub.u2())
        elif name == "InnerClasses" and length >= 2:
            for _ in range(sub.u2()):
                inner = sub.u2()
                outer = sub.u2()
                inner_name = sub.u2()
                flags = sub.u2()
                result["inner_classes"].append({
                    "inner": cp_class(cp, inner),
                    "outer": cp_class(cp, outer) if outer else None,
                    "name": cp_utf8(cp, inner_name) if inner_name else None,
                    "access": access_names(flags),
                })
    return result


def parse_class(data: bytes, include_code_bytes: bool = False) -> Dict[str, Any]:
    reader = Reader(data)
    if reader.u4() != 0xCAFEBABE:
        raise ValueError("invalid class file magic")
    minor = reader.u2()
    major = reader.u2()
    cp_count = reader.u2()
    cp: List[Any] = [None] * cp_count
    index = 1
    while index < cp_count:
        tag = reader.u1()
        if tag == 1:
            cp[index] = ("Utf8", decode_utf8(reader.bytes(reader.u2())))
        elif tag == 3:
            cp[index] = ("Integer", struct.unpack(">i", reader.bytes(4))[0])
        elif tag == 4:
            cp[index] = ("Float", struct.unpack(">f", reader.bytes(4))[0])
        elif tag == 5:
            cp[index] = ("Long", struct.unpack(">q", reader.bytes(8))[0])
            index += 1
        elif tag == 6:
            cp[index] = ("Double", struct.unpack(">d", reader.bytes(8))[0])
            index += 1
        elif tag == 7:
            cp[index] = ("Class", reader.u2())
        elif tag == 8:
            cp[index] = ("String", reader.u2())
        elif tag in {9, 10, 11}:
            cp[index] = ({9: "Fieldref", 10: "Methodref", 11: "InterfaceMethodref"}[tag], reader.u2(), reader.u2())
        elif tag == 12:
            cp[index] = ("NameAndType", reader.u2(), reader.u2())
        elif tag == 15:
            cp[index] = ("MethodHandle", reader.u1(), reader.u2())
        elif tag == 16:
            cp[index] = ("MethodType", reader.u2())
        elif tag in {17, 18}:
            cp[index] = ({17: "Dynamic", 18: "InvokeDynamic"}[tag], reader.u2(), reader.u2())
        elif tag == 19:
            cp[index] = ("Module", reader.u2())
        elif tag == 20:
            cp[index] = ("Package", reader.u2())
        else:
            raise ValueError(f"unsupported constant-pool tag {tag}")
        index += 1

    flags = reader.u2()
    this_name = cp_class(cp, reader.u2())
    super_index = reader.u2()
    super_name = cp_class(cp, super_index) if super_index else None
    interfaces = [cp_class(cp, reader.u2()) for _ in range(reader.u2())]

    fields = []
    for _ in range(reader.u2()):
        field_flags = reader.u2()
        name = cp_utf8(cp, reader.u2())
        descriptor = cp_utf8(cp, reader.u2())
        attrs = read_attributes(reader, cp)
        fields.append({
            "name": name,
            "descriptor": descriptor,
            "field_type": descriptor_type(descriptor)[0],
            "signature": attrs.get("signature"),
            "access": access_names(field_flags, "field"),
            "constant_value": attrs.get("constant_value"),
            "annotations": attrs.get("annotations", []),
        })

    methods = []
    for _ in range(reader.u2()):
        method_flags = reader.u2()
        name = cp_utf8(cp, reader.u2())
        descriptor = cp_utf8(cp, reader.u2())
        attrs = read_attributes(reader, cp, include_code_bytes=include_code_bytes)
        params, return_type = method_descriptor(descriptor)
        names = attrs.get("parameter_names", [])
        code = attrs.get("code")
        if include_code_bytes and code and "_bytes" in code:
            code["instructions"] = disassemble_bytecode(code.pop("_bytes"), cp)
        methods.append({
            "name": name,
            "descriptor": descriptor,
            "full_name": f"{this_name}.{name}{descriptor}",
            "parameter_types": params,
            "return_type": return_type,
            "parameter_names": names,
            "signature": attrs.get("signature"),
            "exceptions": attrs.get("exceptions", []),
            "access": access_names(method_flags, "method"),
            "annotations": attrs.get("annotations", []),
            "parameter_annotations": attrs.get("parameter_annotations", []),
            "code": code,
        })

    attrs = read_attributes(reader, cp)
    if flags & 0x2000:
        kind = "annotation"
    elif flags & 0x0200:
        kind = "interface"
    elif flags & 0x4000:
        kind = "enum"
    else:
        kind = "class"
    package, _, simple = this_name.rpartition(".")
    return {
        "schema_version": SCHEMA,
        "full_name": this_name,
        "name": simple,
        "package": package,
        "kind": kind,
        "classfile": {"minor": minor, "major": major},
        "access": access_names(flags, "class"),
        "super_type": super_name,
        "interfaces": interfaces,
        "signature": attrs.get("signature"),
        "source_file": attrs.get("source_file"),
        "annotations": attrs.get("annotations", []),
        "inner_classes": attrs.get("inner_classes", []),
        "fields": fields,
        "methods": methods,
    }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def detect_game_version(jar_path: Path) -> Optional[str]:
    """Read the game version constant from the current CardCrawlGame class."""
    target = "com/megacrit/cardcrawl/core/CardCrawlGame.class"
    try:
        with zipfile.ZipFile(jar_path) as zf:
            data = zf.read(target)
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    matches = re.findall(rb"(?<![0-9])(?:[0-9]+\.){2}[0-9]+(?![0-9])", data)
    return matches[0].decode("ascii") if matches else None


def parse_manifest(data: bytes) -> Dict[str, str]:
    text = data.decode("utf-8", errors="replace")
    result: Dict[str, str] = {}
    current = None
    for line in text.replace("\r\n", "\n").splitlines():
        if line.startswith(" ") and current:
            result[current] += line[1:]
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current = key.strip()
        result[current] = value.strip()
    return result


def safe_json(data: bytes) -> Optional[Any]:
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def text_preview(data: bytes, limit: int = 2 * 1024 * 1024) -> Optional[str]:
    if len(data) > limit:
        return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if "\x00" in text:
        return None
    return text


def parse_vdf(text: str) -> Dict[str, Any]:
    """Parse the small quoted-key subset used by Steam ACF/VDF files."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\{|\}', text)

    def unquote(value: str) -> str:
        if value.startswith('"') and value.endswith('"'):
            return bytes(value[1:-1], "utf-8").decode("unicode_escape")
        return value

    def block(pos: int) -> Tuple[Dict[str, Any], int]:
        result: Dict[str, Any] = {}
        while pos < len(tokens) and tokens[pos] != "}":
            key = unquote(tokens[pos])
            pos += 1
            if pos >= len(tokens):
                break
            if tokens[pos] == "{":
                value, pos = block(pos + 1)
            else:
                value = unquote(tokens[pos])
                pos += 1
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        if pos < len(tokens) and tokens[pos] == "}":
            pos += 1
        return result, pos

    parsed, _ = block(0)
    return parsed


def portable_path(path: Path, roots: Sequence[Tuple[str, Path]]) -> str:
    for label, root in roots:
        try:
            relative = path.relative_to(root)
            return f"{label}/{relative.as_posix()}"
        except ValueError:
            pass
    return path.name


def workshop_id_for(path: Path) -> Optional[str]:
    for part in path.parts:
        if re.fullmatch(r"\d{8,}", part):
            return part
    return None


def discover_jars(game_root: Path, local_mods: Path, workshop_root: Path) -> List[Dict[str, Any]]:
    paths: List[Path] = []
    base = game_root / "desktop-1.0.jar"
    if base.is_file():
        paths.append(base)
    paths.extend(sorted(local_mods.glob("*.jar")))
    paths.extend(sorted(workshop_root.rglob("*.jar")))
    seen = set()
    specs = []
    roots = [("game", game_root), ("local_mods", local_mods), ("workshop", workshop_root)]
    for path in paths:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            continue
        if path.name == "desktop-1.0.jar":
            scope = "base_game"
        elif path.name in FRAMEWORK_JARS:
            scope = "framework"
        elif path.parent == local_mods:
            scope = "local_mod"
        else:
            scope = "workshop_mod"
        specs.append({
            "path": path,
            "scope": scope,
            "workshop_id": workshop_id_for(path),
            "portable_path": portable_path(path, roots),
        })
    return specs


def read_mod_metadata(zf: zipfile.ZipFile) -> Tuple[Optional[str], Dict[str, Any], List[str], str, Optional[Dict[str, Any]]]:
    candidates = [n for n in zf.namelist() if n.endswith("ModTheSpire.json")]
    if "ModTheSpire.json" in zf.namelist() and "ModTheSpire.json" not in candidates:
        candidates.insert(0, "ModTheSpire.json")
    metadata = None
    source = None
    invalid_fallback: Optional[Dict[str, Any]] = None
    for name in candidates:
        raw = zf.read(name)
        data = safe_json(raw)
        if isinstance(data, dict):
            return source or name, data, candidates, "valid", invalid_fallback
        if invalid_fallback is None:
            invalid_fallback = {
                "path": name,
                "reason": "invalid_json",
                "encoding": "utf-8",
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
                "text": raw.decode("utf-8", errors="replace"),
            }
    if metadata is None:
        for name in zf.namelist():
            if name.lower().endswith(".json") and "mod" in name.lower():
                raw = zf.read(name)
                data = safe_json(raw)
                if isinstance(data, dict) and "modid" in data:
                    source = name
                    metadata = data
                    return source, metadata, candidates, "valid_fallback_candidate", invalid_fallback
    if invalid_fallback is not None:
        return None, {}, candidates, "invalid_json", invalid_fallback
    return None, {}, candidates, "missing", None


def classify_role(spec: Dict[str, Any], full_name: str) -> str:
    jar_name = spec["path"].name
    if jar_name == "desktop-1.0.jar" and full_name.startswith("com.megacrit.cardcrawl."):
        return "base_game"
    if jar_name == "ModTheSpire.jar" and full_name.startswith("com.evacipated.cardcrawl.modthespire"):
        return "modthespire"
    if jar_name == "BaseMod.jar" and full_name.startswith("basemod"):
        return "basemod"
    if jar_name == "StSLib.jar" and full_name.startswith("com.evacipated.cardcrawl.mod.stslib"):
        return "stslib"
    if spec["scope"] in {"local_mod", "workshop_mod"}:
        return "installed_mods"
    return "third_party"


def annotation_types(record: Dict[str, Any]) -> List[str]:
    values = []
    for annotation in record.get("annotations", []):
        value = annotation.get("type")
        if value:
            values.append(value)
    for member in record.get("fields", []) + record.get("methods", []):
        for annotation in member.get("annotations", []):
            value = annotation.get("type")
            if value:
                values.append(value)
    return sorted(set(values))


def class_summary(record: Dict[str, Any], spec: Dict[str, Any], role: str, line: int) -> Dict[str, Any]:
    ann = annotation_types(record)
    return {
        "schema_version": SCHEMA,
        "full_name": record["full_name"],
        "name": record["name"],
        "package": record["package"],
        "kind": record["kind"],
        "role": role,
        "source_jar": spec["path"].name,
        "source_jar_portable_path": spec["portable_path"],
        "line": line,
        "super_type": record.get("super_type"),
        "interfaces": record.get("interfaces", []),
        "annotation_types": ann,
        "method_names": sorted(set(m["name"] for m in record.get("methods", []))),
        "field_names": sorted(set(f["name"] for f in record.get("fields", []))),
        "method_count": len(record.get("methods", [])),
        "field_count": len(record.get("fields", [])),
    }


def mod_candidates(summaries: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    initializer_annotations = {
        "Lcom/evacipated/cardcrawl/modthespire/lib/SpireInitializer;",
    }
    patch_annotations = ANNOTATION_KEYS - initializer_annotations
    initializers = []
    patches = []
    for item in summaries:
        annotations = set(item.get("annotation_types", []))
        if annotations & initializer_annotations or item["super_type"] == "basemod.BaseMod":
            initializers.append(item["full_name"])
        if annotations & patch_annotations or ".patches." in item["full_name"].lower() or item["name"].lower().endswith("patch"):
            patches.append(item["full_name"])
    return {
        "initializer_candidates": sorted(initializers),
        "patch_candidates": sorted(patches),
    }


def _annotation_type_name(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    result = value.get("value")
    if not isinstance(result, str):
        return None
    if result.startswith("[") or result.startswith("L"):
        return descriptor_type(result)[0]
    return result.replace("/", ".")


def _annotation_target_values(value: Any) -> Iterable[Dict[str, Any]]:
    if not isinstance(value, dict):
        return
    if value.get("kind") == "annotation":
        nested = value.get("value")
        if isinstance(nested, dict):
            yield nested
            for child in nested.get("elements", {}).values():
                yield from _annotation_target_values(child)
    elif value.get("kind") == "array":
        for child in value.get("value", []):
            yield from _annotation_target_values(child)


def patch_targets_from_record(record: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    references: List[Dict[str, Any]] = []
    members: List[Tuple[str, Dict[str, Any]]] = [("class", record)]
    members.extend(("field", field) for field in record.get("fields", []))
    members.extend(("method", method) for method in record.get("methods", []))
    for member_kind, member in members:
        for annotation in member.get("annotations", []):
            annotation_type = annotation.get("type", "")
            if "SpirePatch" not in annotation_type:
                continue
            element_sets = [annotation.get("elements", {})]
            element_sets.extend(v for v in _annotation_target_values(annotation.get("elements", {}).get("value")))
            for elements in element_sets:
                target_class_value = elements.get("clz") or elements.get("cls")
                target_method_value = elements.get("method")
                target_class = _annotation_type_name(target_class_value)
                target_method = _annotation_type_name(target_method_value)
                if not target_class or not target_method:
                    continue
                parameters_value = elements.get("paramtypez") or elements.get("paramtypes")
                parameter_values = []
                if isinstance(parameters_value, dict) and parameters_value.get("kind") == "array":
                    parameter_values = [_annotation_type_name(v) for v in parameters_value.get("value", [])]
                elif parameters_value is not None:
                    parameter_values = [_annotation_type_name(parameters_value)]
                references.append({
                    "patch_class": record["full_name"],
                    "patch_member_kind": member_kind,
                    "patch_member": member.get("name"),
                    "patch_source_jar": spec["path"].name,
                    "patch_source_jar_portable_path": spec["portable_path"],
                    "patch_workshop_id": spec["workshop_id"],
                    "annotation_type": annotation_type,
                    "annotation_elements": elements,
                    "target_class": target_class,
                    "target_method": target_method,
                    "target_parameter_types": [x for x in parameter_values if x],
                })
    return references


def inventory_workshop_external_files(workshop_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    by_extension: Counter[str] = Counter()
    by_workshop: Counter[str] = Counter()
    total_bytes = 0
    if not workshop_root.is_dir():
        return records, {"file_count": 0, "total_bytes": 0, "by_extension": {}, "by_workshop_id": {}}
    for path in sorted(workshop_root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() == ".jar":
            continue
        relative = path.relative_to(workshop_root)
        parts = relative.parts
        workshop_id = parts[0] if parts and re.fullmatch(r"\d{8,}", parts[0]) else None
        extension = path.suffix.lower() or "<none>"
        size = path.stat().st_size
        record = {
            "schema_version": SCHEMA,
            "workshop_id": workshop_id,
            "portable_path": f"workshop/{relative.as_posix()}",
            "path_at_generation": str(path),
            "relative_path": relative.as_posix(),
            "name": path.name,
            "extension": extension,
            "size": size,
            "sha256": sha256_file(path),
        }
        records.append(record)
        total_bytes += size
        by_extension[extension] += 1
        by_workshop[workshop_id or "<unknown>"] += 1
    return records, {
        "file_count": len(records),
        "total_bytes": total_bytes,
        "by_extension": dict(sorted(by_extension.items())),
        "by_workshop_id": dict(sorted(by_workshop.items())),
        "note": "Only external files outside Workshop JAR archives are indexed; file bytes are not copied into the knowledge pack.",
    }


def _safe_snapshot_name(class_name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._$-]", "_", class_name)
    suffix = hashlib.sha256(class_name.encode("utf-8")).hexdigest()[:10]
    return f"{safe}.{suffix}.javap.txt"


def _method_matches_target(method: Dict[str, Any], target_method: str, parameter_types: Sequence[str]) -> bool:
    normalized_method = "<init>" if target_method == "<ctor>" else target_method
    if normalized_method in {"<class>", "<clinit>"} or method.get("name") != normalized_method:
        return False
    if not parameter_types:
        return True
    actual = [str(value).replace("/", ".") for value in method.get("parameter_types", [])]
    expected = [str(value).replace("/", ".") for value in parameter_types]
    return actual == expected


def _choose_class_location(locations: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not locations:
        return None
    rank = {"base_game": 0, "framework": 1, "local_mod": 2, "workshop_mod": 3}
    return sorted(locations, key=lambda item: (rank.get(item["spec"]["scope"], 9), item["spec"]["portable_path"]))[0]


def generate_full_game_instruction_snapshots(
    output: Path,
    class_locations: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Capture every parsed method in the current base-game API namespace."""
    bytecode_root = output / "bytecode"
    snapshot_path = bytecode_root / "full_game_instruction_snapshots.jsonl"
    parse_error_path = bytecode_root / "full_game_parse_errors.jsonl"
    base_locations: Dict[str, Dict[str, Any]] = {}
    for class_name, locations in class_locations.items():
        candidates = [
            location for location in locations
            if classify_role(location["spec"], class_name) == "base_game"
        ]
        chosen = _choose_class_location(candidates)
        if chosen is not None:
            base_locations[class_name] = chosen

    by_jar: Dict[Path, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)
    for class_name, location in base_locations.items():
        by_jar[location["spec"]["path"]].append((class_name, location))

    parsed_class_count = 0
    method_count = 0
    methods_with_code = 0
    instruction_count = 0
    parse_errors: List[Dict[str, Any]] = []
    with snapshot_path.open("w", encoding="utf-8") as handle:
        for jar_path in sorted(by_jar, key=lambda value: str(value).lower()):
            with zipfile.ZipFile(jar_path) as zf:
                for class_name, location in sorted(by_jar[jar_path], key=lambda item: item[0]):
                    try:
                        record = parse_class(zf.read(location["entry"]), include_code_bytes=True)
                    except Exception as exc:
                        parse_errors.append({
                            "class": class_name,
                            "source_jar": location["spec"]["path"].name,
                            "source_jar_portable_path": location["spec"]["portable_path"],
                            "entry": location["entry"],
                            "error": str(exc),
                        })
                        continue
                    parsed_class_count += 1
                    for method in record.get("methods", []):
                        key = (class_name, method["name"], method["descriptor"])
                        code = method.get("code")
                        code_metadata = None
                        if code:
                            code_metadata = {key: value for key, value in code.items() if key != "instructions"}
                            methods_with_code += 1
                            instruction_count += len(code.get("instructions", []))
                        snapshot_id = "full-" + hashlib.sha256(
                            "|".join(("base_game",) + key).encode("utf-8")
                        ).hexdigest()[:20]
                        item = {
                            "schema_version": SCHEMA,
                            "snapshot_id": snapshot_id,
                            "coverage": "full_base_game",
                            "target_class": class_name,
                            "target_method": method["name"],
                            "descriptor": method["descriptor"],
                            "source_jar": location["spec"]["path"].name,
                            "source_jar_portable_path": location["spec"]["portable_path"],
                            "classfile": record.get("classfile"),
                            "code": code_metadata,
                            "javap_snapshot": None,
                            "instruction_level": "JVM bytecode (Java IL equivalent; not .NET CLR IL)",
                            "instructions": (code or {}).get("instructions", []) if code else [],
                        }
                        handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
                        method_count += 1
    parse_error_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in parse_errors)
        + ("\n" if parse_errors else ""),
        encoding="utf-8",
    )
    return {
        "full_game_class_count": len(base_locations),
        "full_game_parsed_class_count": parsed_class_count,
        "full_game_parse_error_count": len(parse_errors),
        "full_game_method_count": method_count,
        "full_game_methods_with_code": methods_with_code,
        "full_game_instruction_count": instruction_count,
        "full_game_files": {
            "instruction_snapshots": "bytecode/full_game_instruction_snapshots.jsonl",
            "parse_errors": "bytecode/full_game_parse_errors.jsonl",
        },
    }


def generate_bytecode_artifacts(
    output: Path,
    patch_references: Sequence[Dict[str, Any]],
    class_locations: Dict[str, List[Dict[str, Any]]],
    specs: Sequence[Dict[str, Any]],
    javap_home: Optional[Path],
) -> Dict[str, Any]:
    bytecode_root = output / "bytecode"
    javap_root = bytecode_root / "javap"
    bytecode_root.mkdir(parents=True, exist_ok=True)
    javap_root.mkdir(parents=True, exist_ok=True)
    target_classes = sorted(set(item["target_class"] for item in patch_references))
    parsed_targets: Dict[str, Dict[str, Any]] = {}
    locations: Dict[str, Optional[Dict[str, Any]]] = {}
    parse_errors: List[Dict[str, Any]] = []
    for target_class in target_classes:
        location = _choose_class_location(class_locations.get(target_class, []))
        locations[target_class] = location
        if location is None:
            continue
        try:
            with zipfile.ZipFile(location["spec"]["path"]) as zf:
                data = zf.read(location["entry"])
            parsed_targets[target_class] = {
                "record": parse_class(data, include_code_bytes=True),
                "spec": location["spec"],
                "entry": location["entry"],
            }
        except Exception as exc:
            parse_errors.append({"target_class": target_class, "error": str(exc)})

    javap_executable: Optional[Path] = None
    if javap_home:
        candidate = javap_home / "bin" / ("javap.exe" if os.name == "nt" else "javap")
        if candidate.is_file():
            javap_executable = candidate
    if javap_executable is None:
        found = shutil.which("javap")
        if found:
            javap_executable = Path(found)
    javap_version = None
    javap_errors: List[Dict[str, Any]] = []
    javap_paths: Dict[str, str] = {}
    if javap_executable:
        try:
            version_proc = subprocess.run([str(javap_executable), "-version"], capture_output=True, text=True, timeout=20)
            javap_version = (version_proc.stdout or version_proc.stderr).strip().splitlines()[0] if (version_proc.stdout or version_proc.stderr).strip() else None
        except (OSError, subprocess.SubprocessError) as exc:
            javap_errors.append({"target_class": "<javap-version>", "error": str(exc)})
        for target_class in target_classes:
            location = locations.get(target_class)
            if location is None:
                continue
            existing_snapshot = javap_root / _safe_snapshot_name(target_class)
            if existing_snapshot.is_file():
                javap_paths[target_class] = existing_snapshot.relative_to(output).as_posix()
                continue
            ordered_paths = [location["spec"]["path"]] + [spec["path"] for spec in specs if spec is not location["spec"]]
            classpath = os.pathsep.join(str(path) for path in ordered_paths)
            try:
                proc = subprocess.run(
                    [str(javap_executable), "-classpath", classpath, "-p", "-s", "-c", target_class],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                )
                if proc.returncode == 0:
                    snapshot_path = javap_root / _safe_snapshot_name(target_class)
                    snapshot_path.write_text(proc.stdout, encoding="utf-8")
                    javap_paths[target_class] = snapshot_path.relative_to(output).as_posix()
                else:
                    javap_errors.append({"target_class": target_class, "error": (proc.stderr or proc.stdout).strip()})
            except (OSError, subprocess.SubprocessError) as exc:
                javap_errors.append({"target_class": target_class, "error": str(exc)})

    instruction_path = bytecode_root / "instruction_snapshots.jsonl"
    instruction_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    with instruction_path.open("w", encoding="utf-8") as handle:
        for target_class, parsed in sorted(parsed_targets.items()):
            record = parsed["record"]
            for method in record.get("methods", []):
                key = (target_class, method["name"], method["descriptor"])
                code = method.get("code")
                code_metadata = None
                if code:
                    code_metadata = {key: value for key, value in code.items() if key != "instructions"}
                snapshot_id = hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()[:20]
                item = {
                    "schema_version": SCHEMA,
                    "snapshot_id": snapshot_id,
                    "target_class": target_class,
                    "target_method": method["name"],
                    "descriptor": method["descriptor"],
                    "source_jar": parsed["spec"]["path"].name,
                    "source_jar_portable_path": parsed["spec"]["portable_path"],
                    "classfile": record.get("classfile"),
                    "code": code_metadata,
                    "javap_snapshot": javap_paths.get(target_class),
                    "instruction_level": "JVM bytecode (Java IL equivalent; not .NET CLR IL)",
                    "instructions": (code or {}).get("instructions", []) if code else [],
                }
                handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
                instruction_by_key[key] = item

    patch_target_path = output / "environment" / "patch_targets.jsonl"
    status_counts: Counter[str] = Counter()
    snapshot_counts: Counter[str] = Counter()
    with patch_target_path.open("w", encoding="utf-8") as handle:
        for reference in patch_references:
            target_class = reference["target_class"]
            parsed = parsed_targets.get(target_class)
            location = locations.get(target_class)
            output_item = dict(reference)
            output_item["target_status"] = "missing_class" if parsed is None else "found"
            output_item["target_source_jar"] = parsed["spec"]["path"].name if parsed else None
            output_item["target_source_jar_portable_path"] = parsed["spec"]["portable_path"] if parsed else None
            output_item["javap_snapshot"] = javap_paths.get(target_class)
            output_item["instruction_snapshot_ids"] = []
            if parsed is not None:
                target_method = reference["target_method"]
                if target_method in {"<class>", "<clinit>"}:
                    output_item["target_status"] = "class_target"
                else:
                    matches = [
                        method for method in parsed["record"].get("methods", [])
                        if _method_matches_target(method, target_method, reference.get("target_parameter_types", []))
                    ]
                    if not matches:
                        output_item["target_status"] = "method_not_found"
                        output_item["available_method_descriptors"] = [
                            method["descriptor"] for method in parsed["record"].get("methods", [])
                            if method.get("name") == ("<init>" if target_method == "<ctor>" else target_method)
                        ]
                    else:
                        output_item["matched_method_descriptors"] = [method["descriptor"] for method in matches]
                        output_item["instruction_snapshot_ids"] = [
                            instruction_by_key[(target_class, method["name"], method["descriptor"])]
                            ["snapshot_id"] for method in matches
                        ]
            status_counts[output_item["target_status"]] += 1
            snapshot_counts["with_javap"] += bool(output_item.get("javap_snapshot"))
            snapshot_counts["with_instruction"] += bool(output_item.get("instruction_snapshot_ids"))
            handle.write(json.dumps(output_item, ensure_ascii=False, separators=(",", ":")) + "\n")

    full_game_summary = generate_full_game_instruction_snapshots(output, class_locations)

    if javap_errors:
        (bytecode_root / "javap_errors.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in javap_errors) + "\n",
            encoding="utf-8",
        )
    summary = {
        "schema_version": SCHEMA,
        "patch_reference_count": len(patch_references),
        "unique_target_class_count": len(target_classes),
        "parsed_target_class_count": len(parsed_targets),
        "missing_target_class_count": sum(1 for target in target_classes if target not in parsed_targets),
        "instruction_snapshot_count": len(instruction_by_key),
        "javap_snapshot_count": len(javap_paths),
        "status_counts": dict(sorted(status_counts.items())),
        "javap_version": javap_version,
        "javap_executable_at_generation": str(javap_executable) if javap_executable else None,
        "parse_errors": parse_errors,
        "javap_error_count": len(javap_errors),
        **full_game_summary,
        "files": {
            "patch_targets": "environment/patch_targets.jsonl",
            "instruction_snapshots": "bytecode/instruction_snapshots.jsonl",
            "javap_snapshots": "bytecode/javap/",
            **full_game_summary["full_game_files"],
        },
        "note": "For this Java game, instruction-level IL means JVM bytecode; the full snapshot covers parsed base-game classes, while targeted snapshots and javap text provide patch-focused evidence. No .NET CLR IL is present.",
    }
    (output / "environment" / "patch_target_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (bytecode_root / "README.md").write_text(
        """# 补丁目标字节码快照

`environment/patch_targets.jsonl` records which installed Mod patch annotations point to which target classes/methods.

`full_game_instruction_snapshots.jsonl` contains the parsed JVM instructions for every method in the current `base_game` API namespace (`com.megacrit.cardcrawl.*`). It is the complete base-game method-level bytecode snapshot for this JAR baseline and is intended for on-demand class/method queries.

`instruction_snapshots.jsonl` is the smaller patch-target-focused snapshot. It contains parsed JVM instructions, offsets, operands, constant-pool references, branch targets, and method bytecode hashes. `javap/` contains the corresponding `javap -p -s -c` text snapshots when a JDK tool was available at generation time.

`full_game_parse_errors.jsonl` is an explicit audit list for any base-game class that could not be parsed; an empty file means no parse errors were observed.

Slay the Spire is a Java game, so these are JVM bytecode instructions (Java IL equivalent), not .NET CLR IL. Missing patch classes or methods remain recorded with an explicit status instead of being guessed.
""",
        encoding="utf-8",
    )
    return summary


def generate_docs(
    root: Path,
    counts: Dict[str, Dict[str, int]],
    jars: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    java_info: Dict[str, Any],
    game_root: Path,
    generated_at_utc: str,
    bytecode_summary: Dict[str, Any],
) -> None:
    base = next((j for j in jars if j["name"] == "desktop-1.0.jar"), None)
    basemod = next((m for m in catalog if m.get("jar_name") == "BaseMod.jar"), None)
    mts = next((m for m in catalog if m.get("jar_name") == "ModTheSpire.jar"), None)
    stslib = next((m for m in catalog if m.get("jar_name") == "StSLib.jar"), None)
    def metadata_version(item: Optional[Dict[str, Any]]) -> str:
        metadata = (item or {}).get("metadata", {})
        return str(metadata.get("version") or metadata.get("mts_version") or "未从元数据读取")
    base_count = counts.get("base_game", {})
    doc = f"""# Slay the Spire Mod AI 知识包

这是从本机 Slay the Spire Java 安装和已安装 Mod JAR 生成的、面向 Mod 开发与排错的可查询资料包。它对应生成时的具体文件指纹，不宣称覆盖所有版本。

## 当前基线

- 本体 JAR：`desktop-1.0.jar`，SHA-256：`{base['sha256'] if base else 'missing'}`
- 生成时本体目录：`{game_root}`（仅审计信息；使用时以 `environment/jar_inventory.jsonl` 的 `portable_path` 为准）
- 生成时间：`{generated_at_utc}`（以 `manifest.json` 和 `ai_manifest.json` 为准）
- 本体 `com.megacrit.cardcrawl.*`：{base_count.get('types', 0)} 个类，{base_count.get('methods', 0)} 个方法，{base_count.get('fields', 0)} 个字段
- ModTheSpire 元数据 `mts_version`：{metadata_version(mts)}（该 JAR 的元数据标记，不等同于发布版本号）
- BaseMod：{metadata_version(basemod)}
- StSLib：{metadata_version(stslib)}
- 生成器 Java 运行时：`{java_info.get('version', 'unknown')}`
- 本体 JVM 指令快照：{bytecode_summary.get('full_game_class_count', 0)} 个类、{bytecode_summary.get('full_game_method_count', 0)} 个方法、{bytecode_summary.get('full_game_instruction_count', 0)} 条指令；补丁目标专项快照 {bytecode_summary.get('instruction_snapshot_count', 0)} 个方法

## 给 AI 的读取顺序

1. 先读本文件、`ai_manifest.json` 和 `manifest.json`，确认默认摄取范围与 JAR 指纹。
2. 需要查本体类时，查 `api/base_game_api.types.jsonl`；需要编译 API 时分别查 `api/modthespire_api.types.jsonl`、`api/basemod_api.types.jsonl`、`api/stslib_api.types.jsonl`。
3. 需要理解本机已经装了什么 Mod 时，查 `environment/mod_catalog.json` 和 `api/installed_mods_api.types.jsonl`；Mod 的 `ModTheSpire.json` 元数据、注解和资源路径也被索引。
4. 遇到版本、类路径、资源路径或依赖问题，先查 `environment/jar_inventory.jsonl`、`environment/resource_inventory.jsonl`、`environment/workshop_manifest.json` 和 `environment/workshop_external_files.jsonl`。
5. 遇到补丁目标、Locator 或方法行为问题，查 `environment/patch_targets.jsonl`、`bytecode/instruction_snapshots.jsonl` 和对应的 `bytecode/javap/*.txt`；需要一般本体方法的完整指令时，按需查 `bytecode/full_game_instruction_snapshots.jsonl`。
6. 需要快速定位类/成员时，用 `tools/query-sts-api.ps1`；需要查补丁目标字节码时，用 `tools/query-bytecode.ps1`；需要判断当前 JAR 是否仍与本包一致时，用 `tools/verify-sts-pack.ps1 -VerifyPackFiles -VerifyTemplate`。

默认摄取只包含核心 API、版本摘要、开发文档和工具；`installed_mods`、`third_party`、资源、补丁指令和 HTML 报告都应按任务按需读取，具体以 `ai_file_index.jsonl` 的 `include_by_default`、`role`、`priority` 和 `parse_as` 为准。

## 证据优先级

`api/*.types.jsonl` 中的当前 JAR 结构 > 本机 JAR 的 SHA-256 与元数据 > 本机运行日志和构建结果 > 参考 Mod 的调用模式 > AI 的记忆或旧教程。不要把不同版本的 `desktop-1.0.jar`、ModTheSpire、BaseMod 或 StSLib 混在一起；同名方法必须以描述符和当前 JAR 为准。

## 文档导航

- `docs/MODDING_WORKFLOW.md`：从空项目到能加载的最小 Mod。
- `docs/API_MAP.md`：卡牌、遗物、能力、药水、角色、怪物、战斗动作、事件和 UI 的类图入口。
- `docs/PATCHING_GUIDE.md`：ModTheSpire 注解、Locator、插入/前后缀/替换/字节码补丁。
- `docs/RESOURCE_AND_LOCALIZATION.md`：资源、语言包和 `loadCustomStrings` 的路径规则。
- `docs/TROUBLESHOOTING.md`：日志、依赖、Java 版本和常见加载失败的证据化排查顺序。
- `environment/workshop_external_files.jsonl`：Workshop JAR 外部图片、音频、配置和其他文件的路径/大小/SHA-256 清单。
- `environment/patch_targets.jsonl`、`bytecode/`：补丁注解目标、本体全量 JVM 指令、`javap -p -s -c` 快照和专项指令索引。
- `sts_ai_knowledge_report.html`：无需服务器、双击即可使用的离线类/成员浏览器。
- `templates/`：不依赖绝对路径的最小 Java 8 Mod 模板。

## 边界

- 本包没有复制游戏 JAR、Workshop 外置图片、音频或存档，只记录它们的哈希、类签名和资源索引；这样可以避免把资料包绑定到生成机的绝对路径，也避免把大体积二进制重复分发。
- 类记录包含私有成员和方法代码长度/哈希；本体另有完整 JVM 指令快照，补丁目标另外提供局部 `javap -p -s -c` 文本和专项指令索引，但仍不等同于可读的 Java 源码。
- Java Mod 的“IL”在本包中指 JVM bytecode 指令，不是 .NET CLR IL；目标类/方法不存在或无法解析时会保留明确的状态字段，不会假装生成快照。
- 无效的 `ModTheSpire.json` 会在 `metadata_raw_fallback` 中保留 UTF-8 原文、路径和 SHA-256，供 AI 或人工回退判断。
- `installed_mods` 是生成时本机目录中的快照；创意工坊更新后必须重新生成并重新校验。
"""
    (root / "AI_INGESTION_GUIDE.md").write_text(doc, encoding="utf-8")

    (root / "docs" / "MODDING_WORKFLOW.md").write_text(r"""# Mod 制作工作流

## 1. 运行链路

标准链路是：Steam 游戏目录提供 `desktop-1.0.jar` 和 Java 运行时；ModTheSpire 负责启动、扫描 `ModTheSpire.json`、按依赖排序并对本体类应用补丁；BaseMod 提供订阅者、卡牌/遗物/药水/角色注册和自定义字符串；StSLib 提供可复用的额外机制与接口。

生成时的实际 JAR 和版本写在 `environment/mod_catalog.json`，不要直接把这段概念当成所有版本的保证。

## 2. 最小入口

模板 `templates/src/main/java/example/MinimalMod.java` 使用 `@SpireInitializer`、`BaseMod.subscribe` 和 `PostInitializeSubscriber`。`ModTheSpire.json` 至少需要 `modid`、`name`、`author_list`、`description` 和 `version`；依赖 BaseMod/StSLib 时显式填写 `dependencies`。

```powershell
.\templates\build.ps1 -StsRoot 'E:\Games\SlayTheSpire' -JavaHome 'C:\Program Files\Java\jdk8'
```

脚本会优先从 `$StsRoot\mods` 和 `steamapps\workshop\content\646570` 中查找 ModTheSpire/BaseMod/StSLib。也可以显式传 `-ModTheSpireJar`、`-BaseModJar` 和 `-StSLibJar`。

## 3. 添加内容的最小路径

- 卡牌：继承 `com.megacrit.cardcrawl.cards.AbstractCard`，在初始化阶段 `BaseMod.addCard`；复杂卡牌效果通常在 `use`、`applyPowers`、`calculateCardDamage` 和升级逻辑中完成。
- 遗物：继承 `AbstractRelic` 或 BaseMod 的 `CustomRelic`，使用 `BaseMod.addRelic` 或自定义池注册。
- 能力：继承 `AbstractPower`，由卡牌/遗物通过 `ApplyPowerAction` 等动作施加。
- 药水：继承 `AbstractPotion`，通过 `BaseMod.addPotion` 注册。
- 角色：继承 `AbstractPlayer`，用 BaseMod 的 `addCharacter` 和角色类/颜色枚举完成接入。
- 怪物/遭遇/事件：先查 `base_game_api.types.jsonl` 和 `basemod_api.types.jsonl` 的同名类与注册方法，再照当前版本签名实现。

## 4. 写补丁前先查签名

先用查询工具确认目标类、方法名、参数类型和返回值。补丁目标必须用精确方法描述符区分重载；私有目标可以被补丁框架定位，但 Mod 自己编译时仍应遵守 Java 访问规则，必要时使用 ModTheSpire 的字段/补丁机制，而不是猜字段名。

## 5. 验证标准

1. 用模板或项目自己的构建脚本编译，确保类路径包含本体、ModTheSpire、BaseMod 和实际使用的扩展库。
2. 将生成的 JAR 和 `ModTheSpire.json` 放进正确的 `mods` 目录，使用 ModTheSpire 启动。
3. 检查 `sendToDevs/logs/SlayTheSpire.log`、`sendToDevs/mts_launcher.log` 和启动器输出。
4. 如果行为与知识包不一致，先重新跑 `tools/verify-sts-pack.ps1`；哈希不一致就重新生成，不要继续套用旧签名。
""", encoding="utf-8")

    (root / "docs" / "API_MAP.md").write_text(r"""# API 入口地图

所有名称都应以当前 `api/*.types.jsonl` 的记录为最终依据。下表是搜索入口，不是对方法参数的替代。

| 任务 | 首查类/包 | 常见下一跳 |
|---|---|---|
| 卡牌 | `com.megacrit.cardcrawl.cards.AbstractCard` | `cards.CardGroup`、`cards.CardLibrary`、`actions`、`powers` |
| 遗物 | `com.megacrit.cardcrawl.relics.AbstractRelic` | `relics.AbstractRelic.RelicTier`、`RelicLibrary`、`basemod.helpers.RelicType` |
| 能力 | `com.megacrit.cardcrawl.powers.AbstractPower` | `powers.AbstractPower.PowerType`、`actions.common.ApplyPowerAction` |
| 药水 | `com.megacrit.cardcrawl.potions.AbstractPotion` | `BaseMod.addPotion`、`potions.PotionSlot` |
| 角色 | `com.megacrit.cardcrawl.characters.AbstractPlayer` | `PlayerClass`、`CardColor`、`BaseMod.addCharacter` |
| 怪物 | `com.megacrit.cardcrawl.monsters.AbstractMonster` | `MonsterGroup`、`MonsterInfo`、`getMove`/`takeTurn` |
| 战斗动作 | `com.megacrit.cardcrawl.actions.AbstractGameAction` | `GameActionManager`、`actions.common`、`actions.utility` |
| 地牢状态 | `com.megacrit.cardcrawl.dungeons.AbstractDungeon` | `player`、`actionManager`、抽牌/弃牌/奖励/房间 |
| 游戏状态 | `com.megacrit.cardcrawl.core.CardCrawlGame` | `GameMode`、语言包、屏幕、设置 |
| 事件 | `com.megacrit.cardcrawl.events.AbstractEvent` | `events.AbstractImageEvent`、`EventUtils`、BaseMod 注册 |
| 房间 | `com.megacrit.cardcrawl.rooms.AbstractRoom` | `MapRoomNode`、战斗/商店/篝火房间 |
| UI/图片 | `com.megacrit.cardcrawl.helpers.ImageMaster` | `TextureAtlas`、`FontHelper`、`Hitbox`、`UIElement` |
| 字符串 | `com.megacrit.cardcrawl.localization.*` | `CardStrings`、`RelicStrings`、`PowerStrings`、`PotionStrings` |
| Mod 订阅 | `basemod.interfaces.*Subscriber` | `BaseMod.subscribe`、`receive...` 生命周期 |
| 字段扩展 | `com.evacipated.cardcrawl.modthespire.lib.SpireField` | `StaticSpireField`、`initialize/get/set` |
| 补丁 | `com.evacipated.cardcrawl.modthespire.lib.SpirePatch*` | Locator、Matcher、`SpireReturn`、`LineFinder` |
| 扩展机制 | `com.evacipated.cardcrawl.mod.stslib.*` | 卡牌/遗物/能力接口和对应 patch |

## 推荐查询

```powershell
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role base_game -TypeName AbstractCard
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role basemod -TypeName BaseMod -Member addCard
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role modthespire -TypeName '*SpirePatch*'
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role installed_mods -Member 'receive*'
```

查询结果中的 `descriptor` 是 JVM 的真实签名；同名重载必须同时看它和 `parameter_types`。
""", encoding="utf-8")

    (root / "docs" / "PATCHING_GUIDE.md").write_text("""# ModTheSpire 补丁要点

## 补丁类型

- `@SpirePatch` / `@SpirePatch2`：指向类、方法和可选参数类型。`SpirePatch2` 是当前 JAR 中的独立注解，必须以 API JSONL 的注解属性为准。
- `@SpirePrefixPatch`：目标方法执行前运行；返回 `void` 表示继续，使用 `SpireReturn.Return(...)` 或相关返回值机制时可以短路（先查当前 `SpireReturn` 签名）。
- `@SpirePostfixPatch`：目标方法正常执行后运行，可接收原返回值并返回修改后的值。
- `@SpireInsertPatch`：在目标方法内部插入，通常配合 `SpireInsertLocator`、`LineFinder`、`Matcher`；`loc/rloc/locs/rlocs` 与 `localvars` 的具体属性在当前 API 记录里。
- `@SpireInstrumentPatch`：使用 Javassist `ExprEditor` 等机制改写方法体，脆弱度最高。
- `@SpireRawPatch`：直接接触原始字节码时使用，只有在普通补丁无法满足需求时考虑。
- `@SpireField` / `StaticSpireField`：给原类增加实例/静态扩展字段，不要直接假设本体私有字段在下一版本仍存在。

## 写补丁的顺序

1. 从 `api/base_game_api.types.jsonl` 找目标类和目标重载。
2. 用 `tools/query-sts-api.ps1 -IncludeBody` 看方法的代码长度/哈希和补丁类已有的注解属性；优先查 `environment/patch_targets.jsonl` 与 `bytecode/instruction_snapshots.jsonl`，再用对应的 `bytecode/javap/*.txt` 或 `tools/javap-type.ps1 -Bytecode` 做行为确认。
3. 选择最小补丁：前缀/后缀优先，其次插入，最后才是 Instrument/Raw。
4. 如果目标属于可选 Mod，填写 `requiredModId` 或 `optional`，并在 `ModTheSpire.json` 中区分硬依赖和可选依赖。
5. 一次只引入一个补丁目标，启动后检查日志中的 patch 应用结果。

## Locator 不能靠猜

插入点由字节码指令决定；源码行号、反编译出来的局部变量名和旧版教程都不能替代当前 JAR。类记录中的 `code.sha256` 只用于发现目标是否变了；`bytecode/instruction_snapshots.jsonl` 才包含偏移、操作码、操作数、常量池引用和分支目标。目标方法变更后应重新确定 Matcher/Locator，而不是只改注解名字。

## 常见误区

- 把构造器写成普通方法名：JVM 描述符里构造器是 `<init>`。
- 只写类名不写参数：重载会命中错误方法或根本无法应用。
- 用 `@SpirePatch` 的旧属性名替代当前 `clz/cls/method/paramtypez/paramtypes`。
- 把 BaseMod 订阅接口当作 ModTheSpire 补丁：前者是生命周期回调，后者是字节码补丁，两条链路可以并存。
- 在没有验证当前 JAR 哈希的情况下引用旧的 `Locator` 行号。
""", encoding="utf-8")

    (root / "docs" / "RESOURCE_AND_LOCALIZATION.md").write_text("""# 资源与本地化

## 路径规则

Mod JAR 内资源路径是相对于 JAR 根目录的正斜杠路径，代码通过 `Class.getResource`、`Gdx.files.internal`、`ImageMaster` 或 BaseMod 的加载器访问。不要把 `E:\\SteamLibrary...` 写进 Mod；把资源放在自己的前缀目录下，例如 `mymodResources/images/...` 和 `mymodResources/localization/eng/...`。

本机已安装 Mod 的 JAR 内资源路径可查 `environment/resource_inventory.jsonl`；JAR 外部的 Workshop 图片、音频、配置和其他文件可查 `environment/workshop_external_files.jsonl`。两者都只提供路径和指纹，不把二进制内容复制进知识库。

## 字符串

常见字符串对象包括 `CardStrings`、`RelicStrings`、`PowerStrings`、`PotionStrings`、`CharacterStrings`、`EventStrings` 和 `UIStrings`。推荐在初始化阶段使用 `BaseMod.loadCustomStrings` 或 `loadCustomStringsFile`，再用类的 `get` 方法取得对应 ID；实际 JSON 文件名和对象结构以当前 BaseMod/API 与已安装 Mod 的文本资源为准。

## 图片和动画

卡牌通常需要攻击/技能/能力的卡图；遗物需要图标和 outline；角色与怪物可能需要 Spine JSON/atlas/png。不要只改路径字符串就认为资源加载成功：同时检查资源确实在 JAR、大小/路径出现在资源索引，并从运行日志确认加载阶段没有 `FileNotFoundException` 或 Spine 解析异常。

## 中文与编码

生成器以 UTF-8 读取并写出 JSON 文本，保留 BOM 兼容读取。中文本地化文件建议保持 UTF-8，并把 `zhs`/`zht` 等语言目录与当前游戏约定对齐。AI 生成新文本时应复用现有 Mod 的字段结构，而不是把描述字符串硬编码进卡牌类。
""", encoding="utf-8")

    (root / "docs" / "TROUBLESHOOTING.md").write_text("""# 排错手册

## 先做三项确认

1. `powershell -NoProfile -ExecutionPolicy Bypass -File .\\tools\\verify-sts-pack.ps1 -GameRoot 'E:\\Games\\SlayTheSpire' -PackRoot $PWD`。
2. 确认 `desktop-1.0.jar`、ModTheSpire、BaseMod、StSLib 的 SHA-256 与 `environment/jar_inventory.jsonl` 一致。
3. 读取当前游戏目录下 `sendToDevs/logs/SlayTheSpire.log`、`sendToDevs/mts_launcher.log`，不要只看旧截图或旧教程。

## 日志关键词

- `NoClassDefFoundError` / `ClassNotFoundException`：类路径或依赖缺失。
- `NoSuchMethodError` / `NoSuchFieldError`：编译时 JAR 与运行时 JAR 不一致，或 API 版本不匹配。
- `VerifyError` / `IllegalAccessError`：补丁生成的字节码、访问级别或 Java 版本不兼容。
- patch application failed、Locator、Matcher：目标方法或字节码布局已经变了，重新查描述符并重新设计 Locator。
- `FileNotFoundException`、Spine/Texture 异常：JAR 内资源路径、大小写、前缀或 atlas/png 配套不一致。

## Java 版本

本机游戏自带 JRE 为生成时实际可见的版本，写入 `environment/environment_manifest.json`。模板默认编译到 Java 8 字节码以适配这套启动链路；但已安装模组的构建 JDK 可能是 17 或 21，JAR 的 `classfile.major` 会如实记录。若运行时是 Java 8，直接加载更高 major 的 Mod 会失败；应以当前启动器和日志为准，不要仅凭 `Build-Jdk` 字段判断运行时。

## 依赖顺序

`ModTheSpire.json` 的 `dependencies` 是加载依赖；`optional_dependencies` 不应被当成硬依赖。先检查 `environment/mod_catalog.json` 的元数据，再检查实际 JAR 是否存在；只在类确实被引用时才把 StSLib 或其他 Mod 设为硬依赖。

如果 `metadata_status` 为 `invalid_json`，不要把空的 `metadata` 当成“没有元数据”；读取同一条记录的 `metadata_raw_fallback.text`，并结合 `metadata_raw_fallback.sha256` 判断原文是否发生变化。

## 版本不一致时

不要手工编辑 API JSONL 来“修正”版本。保留旧包，换新的输出目录重新跑生成器，再重新运行验证工具；这样 AI 能区分不同基线。
""", encoding="utf-8")


def write_query_tool(root: Path) -> None:
    (root / "tools" / "query-sts-api.ps1").write_text(r'''[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [ValidateSet('base_game','modthespire','basemod','stslib','installed_mods','third_party')]
    [string]$Role = 'base_game',
    [Parameter(Mandatory = $true)] [string]$TypeName,
    [string]$Member,
    [switch]$IncludeBody
)

$ErrorActionPreference = 'Stop'
$files = @{
    base_game = 'base_game_api.types.jsonl'
    modthespire = 'modthespire_api.types.jsonl'
    basemod = 'basemod_api.types.jsonl'
    stslib = 'stslib_api.types.jsonl'
    installed_mods = 'installed_mods_api.types.jsonl'
    third_party = 'third_party_api.types.jsonl'
}
$jsonl = Join-Path ([IO.Path]::GetFullPath($PackRoot)) ('api\' + $files[$Role])
if (-not (Test-Path -LiteralPath $jsonl -PathType Leaf)) { throw "API JSONL not found: $jsonl" }
$results = New-Object System.Collections.Generic.List[object]
foreach ($line in Get-Content -LiteralPath $jsonl -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $record = $line | ConvertFrom-Json
    if (($record.full_name -ne $TypeName) -and ($record.name -ne $TypeName) -and ($record.full_name -notlike $TypeName)) { continue }
    if ([string]::IsNullOrWhiteSpace($Member)) {
        if ($IncludeBody) { $results.Add($record); continue }
        $results.Add([pscustomobject][ordered]@{
            full_name = $record.full_name
            source_jar = $record.source_jar
            super_type = $record.super_type
            interfaces = @($record.interfaces)
            kind = $record.kind
            annotations = @($record.annotations)
            methods = @($record.methods | ForEach-Object {
                [pscustomobject][ordered]@{ name=$_.name; descriptor=$_.descriptor; return_type=$_.return_type; parameter_types=@($_.parameter_types); access=@($_.access); exceptions=@($_.exceptions); code=$_.code }
            })
            fields = @($record.fields | ForEach-Object {
                [pscustomobject][ordered]@{ name=$_.name; descriptor=$_.descriptor; field_type=$_.field_type; access=@($_.access); constant_value=$_.constant_value }
            })
        })
        continue
    }
    $methods = @($record.methods | Where-Object { $_.name -like $Member -or $_.full_name -like $Member })
    $fields = @($record.fields | Where-Object { $_.name -like $Member })
    if (($methods.Count + $fields.Count) -gt 0) {
        $results.Add([pscustomobject][ordered]@{ full_name=$record.full_name; source_jar=$record.source_jar; methods=$methods; fields=$fields })
    }
}
if ($results.Count -eq 0) { throw "No match. Role=$Role TypeName=$TypeName Member=$Member" }
$results | ConvertTo-Json -Depth 100
''', encoding="utf-8")


def write_verify_tool(root: Path) -> None:
    (root / "tools" / "verify-sts-pack.ps1").write_text(r'''[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$GameRoot,
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [switch]$VerifyPackFiles,
    [switch]$VerifyWorkshopExternalFiles,
    [switch]$VerifyTemplate
)

$ErrorActionPreference = 'Stop'
$gameRoot = [IO.Path]::GetFullPath($GameRoot)
$packRoot = [IO.Path]::GetFullPath($PackRoot)
$manifest = Get-Content -LiteralPath (Join-Path $packRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = New-Object System.Collections.Generic.List[string]
$ignoredRoots = @('.git', '.hg', '.svn', '__pycache__')
$packPrefix = $packRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

function Normalize-RelativePath([string]$Path) {
    return $Path.Replace('\', '/')
}

function Test-IgnoredPackPath([string]$RelativePath) {
    $normalized = Normalize-RelativePath $RelativePath
    $parts = $normalized.Split('/')
    return ($parts[0] -in $ignoredRoots) -or $normalized -like 'templates/build/*' -or $normalized -like '*.pyc'
}

function Resolve-PackPath([string]$RelativePath) {
    $normalized = Normalize-RelativePath $RelativePath
    if ([IO.Path]::IsPathRooted($normalized) -or $normalized -eq '..' -or $normalized -like '../*') {
        throw "path is absolute or escapes pack root: $RelativePath"
    }
    $resolved = [IO.Path]::GetFullPath((Join-Path $packRoot ($normalized -replace '/', [IO.Path]::DirectorySeparatorChar)))
    if (-not $resolved.StartsWith($packPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "path escapes pack root: $RelativePath"
    }
    return $resolved
}

$steamapps = Split-Path (Split-Path $gameRoot)
$workshopRoot = Join-Path $steamapps 'workshop\content\646570'
foreach ($jar in @($manifest.jars)) {
    $portable = [string]$jar.portable_path
    if ($portable -like 'workshop/*') {
        $relative = $portable.Substring(9) -replace '/', [IO.Path]::DirectorySeparatorChar
        $actual = Join-Path $workshopRoot $relative
    }
    elseif ($portable -like 'game/*') {
        $relative = $portable.Substring(5) -replace '/', [IO.Path]::DirectorySeparatorChar
        $actual = Join-Path $gameRoot $relative
    }
    else { $actual = Join-Path $gameRoot (($portable) -replace '/', [IO.Path]::DirectorySeparatorChar) }
    if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { $failures.Add("missing $($jar.name) [$portable]: $actual"); continue }
    $item = Get-Item -LiteralPath $actual
    $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
    if (($item.Length -ne [int64]$jar.size) -or ($hash -ne ([string]$jar.sha256).ToUpperInvariant())) { $failures.Add("mismatch $($jar.name) [$portable]: sizeOk=$($item.Length -eq [int64]$jar.size) hashOk=$($hash -eq ([string]$jar.sha256).ToUpperInvariant())") }
    else { Write-Host "OK   $($jar.name) $hash" -ForegroundColor Green }
}
if ($VerifyWorkshopExternalFiles) {
    $externalIndex = Join-Path $packRoot 'environment\workshop_external_files.jsonl'
    if (-not (Test-Path -LiteralPath $externalIndex -PathType Leaf)) { $failures.Add("missing external Workshop index: $externalIndex") }
    else {
        foreach ($line in Get-Content -LiteralPath $externalIndex -Encoding UTF8) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try { $entry = $line | ConvertFrom-Json } catch { $failures.Add("invalid external Workshop JSON: $($_.Exception.Message)"); continue }
            $portable = [string]$entry.portable_path
            if ($portable -notlike 'workshop/*') { $failures.Add("invalid external Workshop path: $portable"); continue }
            $relative = $portable.Substring(9) -replace '/', [IO.Path]::DirectorySeparatorChar
            $actual = Join-Path $workshopRoot $relative
            if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { $failures.Add("missing external Workshop file [$portable]: $actual"); continue }
            $item = Get-Item -LiteralPath $actual
            $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
            if ($item.Length -ne [int64]$entry.size -or $hash -ne ([string]$entry.sha256).ToUpperInvariant()) { $failures.Add("external Workshop mismatch: $portable") }
        }
    }
}
if ($VerifyPackFiles) {
    $index = Join-Path $packRoot 'ai_file_index.jsonl'
    if (-not (Test-Path -LiteralPath $index -PathType Leaf)) {
        $failures.Add("missing pack file index: $index")
    }
    $seen = @{}
    $checked = 0
    if (Test-Path -LiteralPath $index -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $index -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $entry = $line | ConvertFrom-Json } catch { $failures.Add("invalid pack index JSON: $($_.Exception.Message)"); continue }
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative)) { $failures.Add('pack index entry has no path'); continue }
        $normalized = Normalize-RelativePath $relative
        if (Test-IgnoredPackPath $normalized) { $failures.Add("pack index contains excluded path: $normalized"); continue }
        if ($seen.ContainsKey($normalized)) { $failures.Add("duplicate pack index path: $normalized"); continue }
        $seen[$normalized] = $true
        try { $file = Resolve-PackPath $normalized } catch { $failures.Add($_.Exception.Message); continue }
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("missing pack file: $normalized"); continue }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToUpperInvariant()
        $size = (Get-Item -LiteralPath $file).Length
        if ($size -ne [int64]$entry.size -or $hash -ne ([string]$entry.sha256).ToUpperInvariant()) { $failures.Add("pack file mismatch: $normalized") }
        else { $checked++ }
    }
    foreach ($file in Get-ChildItem -LiteralPath $packRoot -File -Recurse -Force) {
        $relative = Normalize-RelativePath ($file.FullName.Substring($packRoot.Length + 1))
        if ($relative -eq 'ai_file_index.jsonl' -or (Test-IgnoredPackPath $relative)) { continue }
        if (-not $seen.ContainsKey($relative)) { $failures.Add("unindexed pack file: $relative") }
    }
    Write-Host "Pack file verification checked $checked file(s)."
    }
}
if ($VerifyTemplate) {
    $templateFiles = @(
        'templates/build.ps1',
        'templates/ModTheSpire.json',
        'templates/README.md',
        'templates/src/main/java/example/MinimalMod.java'
    )
    foreach ($relative in $templateFiles) {
        try { $file = Resolve-PackPath $relative } catch { $failures.Add($_.Exception.Message); continue }
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("missing template file: $relative") }
    }
    $metadataPath = Join-Path $packRoot 'templates\ModTheSpire.json'
    if (Test-Path -LiteralPath $metadataPath -PathType Leaf) {
        try {
            $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($key in @('modid', 'name', 'author_list', 'description', 'version')) {
                if ($null -eq $metadata.PSObject.Properties[$key]) { $failures.Add("template metadata missing key: $key") }
            }
        } catch { $failures.Add("invalid template ModTheSpire.json: $($_.Exception.Message)") }
    }
}
$aiManifestPath = Join-Path $packRoot 'ai_manifest.json'
if (-not (Test-Path -LiteralPath $aiManifestPath -PathType Leaf)) {
    $failures.Add("missing AI manifest: $aiManifestPath")
} else {
    try {
        $aiManifest = Get-Content -LiteralPath $aiManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($key in @('pack_id', 'pack_version', 'generated_at_utc', 'ingestion_order', 'default_files', 'on_demand_files')) {
            if ($null -eq $aiManifest.PSObject.Properties[$key]) { $failures.Add("AI manifest missing key: $key") }
        }
    } catch { $failures.Add("invalid AI manifest: $($_.Exception.Message)") }
}
if ($failures.Count) { $failures | ForEach-Object { Write-Host "FAIL $_" -ForegroundColor Red }; exit 1 }
Write-Host 'Verification passed.' -ForegroundColor Green
''', encoding="utf-8")


def write_javap_tool(root: Path) -> None:
    (root / "tools" / "javap-type.ps1").write_text(r'''[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$JavaHome,
    [Parameter(Mandatory = $true)] [string]$TypeName,
    [Parameter(Mandatory = $true)] [string[]]$Jar,
    [switch]$Bytecode
)
$ErrorActionPreference = 'Stop'
$javap = Join-Path ([IO.Path]::GetFullPath($JavaHome)) 'bin\javap.exe'
if (-not (Test-Path -LiteralPath $javap)) { throw "javap.exe not found: $javap" }
$cp = $Jar -join [IO.Path]::PathSeparator
$args = @('-classpath', $cp, '-p', '-s')
if ($Bytecode) { $args += '-c' }
$args += $TypeName
& $javap @args
exit $LASTEXITCODE
''', encoding="utf-8")


def write_bytecode_query_tool(root: Path) -> None:
    (root / "tools" / "query-bytecode.ps1").write_text(r'''[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [string]$TargetClass,
    [string]$TargetMethod,
    [string]$PatchClass,
    [switch]$FullGame,
    [switch]$IncludeInstructions
)

$ErrorActionPreference = 'Stop'
$packRoot = [IO.Path]::GetFullPath($PackRoot)
$targetFile = Join-Path $packRoot 'environment\patch_targets.jsonl'
if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) { throw "Patch target index not found: $targetFile" }
$targetMatches = New-Object System.Collections.Generic.List[object]
foreach ($line in Get-Content -LiteralPath $targetFile -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $item = $line | ConvertFrom-Json
    if ($TargetClass -and $item.target_class -notlike $TargetClass) { continue }
    if ($TargetMethod -and $item.target_method -notlike $TargetMethod) { continue }
    if ($PatchClass -and $item.patch_class -notlike $PatchClass) { continue }
    $targetMatches.Add($item)
}
if (-not $IncludeInstructions -and -not $FullGame) { @($targetMatches.ToArray()) | ConvertTo-Json -Depth 100; exit 0 }
$snapshotFile = Join-Path $packRoot 'bytecode\instruction_snapshots.jsonl'
$wanted = @{}
foreach ($item in $targetMatches) { foreach ($id in @($item.instruction_snapshot_ids)) { $wanted[[string]$id] = $true } }
$snapshots = New-Object System.Collections.Generic.List[object]
if (Test-Path -LiteralPath $snapshotFile -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $snapshotFile -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $item = $line | ConvertFrom-Json
        if ($wanted.ContainsKey([string]$item.snapshot_id)) { $snapshots.Add($item) }
    }
}
$fullSnapshots = New-Object System.Collections.Generic.List[object]
if ($FullGame) {
    $fullFile = Join-Path $packRoot 'bytecode\full_game_instruction_snapshots.jsonl'
    if (-not (Test-Path -LiteralPath $fullFile -PathType Leaf)) { throw "Full base-game bytecode index not found: $fullFile" }
    foreach ($line in Get-Content -LiteralPath $fullFile -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $item = $line | ConvertFrom-Json
        if ($TargetClass -and $item.target_class -notlike $TargetClass) { continue }
        if ($TargetMethod -and $item.target_method -notlike $TargetMethod) { continue }
        $fullSnapshots.Add($item)
    }
}
$result = [ordered]@{ patch_targets=@($targetMatches.ToArray()) }
if ($IncludeInstructions) { $result.instruction_snapshots = @($snapshots.ToArray()) }
if ($FullGame) { $result.full_game_instruction_snapshots = @($fullSnapshots.ToArray()) }
[pscustomobject]$result | ConvertTo-Json -Depth 100
''', encoding="utf-8")


def write_html_report(root: Path, api_counts: Dict[str, Dict[str, int]], api_index: Dict[str, List[Dict[str, Any]]], jar_inventory: List[Dict[str, Any]], game_version: str) -> None:
    entries = [item for role in sorted(api_index) for item in api_index[role]]
    payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    role_meta = {
        "base_game": {"label": "本体 API", "short": "本体", "class": "blue"},
        "modthespire": {"label": "ModTheSpire", "short": "MTS", "class": "purple"},
        "basemod": {"label": "BaseMod", "short": "BaseMod", "class": "green"},
        "stslib": {"label": "StSLib", "short": "StSLib", "class": "teal"},
        "installed_mods": {"label": "已安装 Mod", "short": "已装 Mod", "class": "orange"},
        "third_party": {"label": "第三方库", "short": "第三方", "class": "gray"},
    }

    def number(value: Any) -> str:
        return f"{int(value):,}"

    def metadata_version(item: Optional[Dict[str, Any]]) -> str:
        metadata = (item or {}).get("metadata", {})
        return str(metadata.get("version") or metadata.get("mts_version") or "未读取")

    core_workshop_ids = {"1605060445", "1605833019", "1609158507"}
    api_library_groups: Dict[str, Dict[str, Any]] = {}
    for item in jar_inventory:
        workshop_id = str(item.get("workshop_id") or "")
        if workshop_id not in WORKSHOP_API_IDS:
            continue
        metadata = item.get("metadata") or {}
        group = api_library_groups.setdefault(workshop_id, {
            "name": str(metadata.get("name") or item.get("name") or workshop_id),
            "jars": [],
            "dependencies": set(),
            "types": 0,
        })
        group["jars"].append(str(item.get("portable_path") or item.get("name") or ""))
        group["types"] += int(item.get("class_count", 0))
        for dependency in metadata.get("dependencies") or []:
            group["dependencies"].add(str(dependency))

    api_library_rows = []
    for workshop_id in sorted(WORKSHOP_API_IDS, key=lambda value: (value not in api_library_groups, value)):
        group = api_library_groups.get(workshop_id)
        name = str((group or {}).get("name") or f"Workshop item {workshop_id}")
        category = "核心框架" if workshop_id in core_workshop_ids else "API 专用库/框架"
        jars = "<br>".join(html.escape(value) for value in (group or {}).get("jars", [])) or "—"
        dependencies = ", ".join(sorted((group or {}).get("dependencies", set()))) or "—"
        state = "已扫描" if group else "未发现"
        state_class = "ok" if group else "missing"
        api_library_rows.append(
            "<tr>"
            f"<td><span class='mini-badge {'green' if workshop_id in core_workshop_ids else 'purple'}'>{category}</span></td>"
            f"<td><strong>{html.escape(name)}</strong><small>Workshop {html.escape(workshop_id)}</small></td>"
            f"<td class='jar-list'>{jars}</td>"
            f"<td>{html.escape(dependencies)}</td>"
            f"<td>{number((group or {}).get('types', 0))}</td>"
            f"<td><span class='state {state_class}'>{state}</span></td>"
            "</tr>"
        )
    api_library_html = "".join(api_library_rows)
    api_library_present = sum(1 for workshop_id in WORKSHOP_API_IDS if workshop_id in api_library_groups)

    def jar_by_name(name: str) -> Optional[Dict[str, Any]]:
        return next((item for item in jar_inventory if item.get("name") == name), None)

    resource_count = sum(int(item.get("resource_count", 0)) for item in jar_inventory)
    text_resource_count = sum(int(item.get("resource_text_count", 0)) for item in jar_inventory)
    workshop_count = sum(1 for item in jar_inventory if item.get("scope") == "workshop_mod")
    framework_count = sum(1 for item in jar_inventory if item.get("scope") == "framework")
    base_jar_count = sum(1 for item in jar_inventory if item.get("scope") == "base_game")
    local_count = sum(1 for item in jar_inventory if item.get("scope") == "local_mod")
    total_types = sum(int(data.get("types", 0)) for data in api_counts.values())
    base = jar_by_name("desktop-1.0.jar") or {}
    mts = jar_by_name("ModTheSpire.jar") or {}
    basemod = jar_by_name("BaseMod.jar") or {}
    stslib = jar_by_name("StSLib.jar") or {}

    badge_html = "".join([
        f"<span class='badge badge-blue'>desktop-1.0.jar · {html.escape(str(base.get('sha256', ''))[:12])}</span>",
        f"<span class='badge badge-purple'>ModTheSpire · {html.escape(metadata_version(mts))}</span>",
        f"<span class='badge badge-green'>BaseMod · {html.escape(metadata_version(basemod))}</span>",
        f"<span class='badge badge-teal'>StSLib · {html.escape(metadata_version(stslib))}</span>",
        f"<span class='badge badge-orange'>{number(len(jar_inventory))} 个 JAR / {number(resource_count)} 个资源</span>",
        f"<span class='badge badge-orange'>游戏版本 {html.escape(game_version)}</span>",
        f"<span class='badge badge-gray'>Workshop API 库 {number(api_library_present)}/{number(len(WORKSHOP_API_IDS))}</span>",
    ])

    stat_cards = "".join([
        f"<div class='stat-card'><div class='stat-value'>{number(api_counts.get('base_game', {}).get('types', 0))}</div><div class='stat-label'>本体 API 类型</div></div>",
        f"<div class='stat-card'><div class='stat-value'>{number(api_counts.get('base_game', {}).get('methods', 0))}</div><div class='stat-label'>本体 API 方法</div></div>",
        f"<div class='stat-card'><div class='stat-value'>{number(api_counts.get('base_game', {}).get('fields', 0))}</div><div class='stat-label'>本体 API 字段</div></div>",
        f"<div class='stat-card'><div class='stat-value'>{number(api_counts.get('installed_mods', {}).get('types', 0))}</div><div class='stat-label'>已安装 Mod 类型</div></div>",
        f"<div class='stat-card'><div class='stat-value'>{number(text_resource_count)}</div><div class='stat-label'>文本/本地化资源</div></div>",
    ])

    fingerprint_rows = []
    for item, role, label in [
        (base, "base_game", "本体 JAR"),
        (mts, "modthespire", "ModTheSpire"),
        (basemod, "basemod", "BaseMod"),
        (stslib, "stslib", "StSLib"),
    ]:
        metadata = item.get("metadata", {})
        version = metadata.get("version") or metadata.get("mts_version") or "—"
        fingerprint_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(label)}</strong><small>{html.escape(role_meta.get(role, {}).get('label', role))}</small></td>"
            f"<td><code>{html.escape(str(item.get('portable_path', '')))}</code></td>"
            f"<td>{number(item.get('size', 0))}<small> bytes</small></td>"
            f"<td class='hash'><code>{html.escape(str(item.get('sha256', '')))}</code></td>"
            f"<td><span class='mini-badge {role_meta.get(role, {}).get('class', 'gray')}'>{html.escape(str(version))}</span></td>"
            "</tr>"
        )
    fingerprint_html = "".join(fingerprint_rows)

    coverage_rows = []
    role_order = ["base_game", "modthespire", "basemod", "stslib", "installed_mods", "third_party"]
    for role in role_order:
        data = api_counts.get(role, {})
        meta = role_meta[role]
        coverage_rows.append(
            f"<tr><td><span class='role-dot {meta['class']}'></span><strong>{meta['label']}</strong><small>{role}</small></td>"
            f"<td>{number(data.get('types', 0))}</td><td>{number(data.get('methods', 0))}</td><td>{number(data.get('fields', 0))}</td>"
            f"<td><div class='coverage-bar'><i class='{meta['class']}' style='width:{min(100, max(3, int(data.get('types', 0) / max(total_types, 1) * 100)))}%'></i></div></td></tr>"
        )
    coverage_html = "".join(coverage_rows)
    role_json = json.dumps(role_meta, ensure_ascii=False, separators=(",", ":"))

    report = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Slay the Spire · 完整 Mod API 知识报告</title>
<style>
:root{{--ink:#172033;--muted:#647087;--line:#e8e7ee;--panel:#fff;--bg:#f7f7f8;--blue:#5448d8;--purple:#7658d8;--green:#159276;--teal:#168f9a;--orange:#d9822b;--shadow:0 10px 28px rgba(31,34,60,.08)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI","Microsoft YaHei",sans-serif;font-size:14px;line-height:1.65}}
.page{{max-width:1160px;margin:0 auto;padding:28px 18px 70px}}.hero{{border:1px solid #dfddf4;border-radius:18px;padding:28px 30px 25px;background:linear-gradient(135deg,#fbfbff 0%,#f0efff 100%);box-shadow:var(--shadow)}}
.eyebrow{{color:#4f43c5;font-size:12px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase}}h1{{font-size:34px;line-height:1.2;margin:8px 0 10px;letter-spacing:-.5px}}.hero p{{color:#58647a;font-size:15px;margin:0;max-width:880px}}.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}.badge,.mini-badge{{display:inline-flex;align-items:center;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700}}.badge-blue,.mini-badge.blue{{background:#eeedff;color:#5042c8}}.badge-purple,.mini-badge.purple{{background:#f0eaff;color:#7850bd}}.badge-green,.mini-badge.green{{background:#e5f7f0;color:#168267}}.badge-teal,.mini-badge.teal{{background:#e4f7f8;color:#16808a}}.badge-orange,.mini-badge.orange{{background:#fff0d9;color:#b56a16}}.badge-gray,.mini-badge.gray{{background:#eef0f4;color:#5c6675}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0}}.stat-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:17px 12px;text-align:center;box-shadow:var(--shadow)}}.stat-value{{font-size:27px;font-weight:800;color:#5146c9;line-height:1.15}}.stat-label{{color:#6c7485;margin-top:5px;font-size:13px}}
.callout{{background:#fff2d8;border:1px solid #f6dba6;border-radius:13px;padding:14px 17px;color:#765217;margin-bottom:28px}}.callout strong{{color:#9b6711}}.section{{margin-top:30px}}.section-title{{display:flex;align-items:center;gap:12px;border-bottom:2px solid #5046d0;padding:0 0 9px;margin:0 0 13px;font-size:22px}}.section-title span{{color:#9da2b0;font-size:14px;font-weight:500}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:15px;box-shadow:var(--shadow);overflow:hidden}}.panel-pad{{padding:18px 20px}}table{{width:100%;border-collapse:collapse}}th{{background:#efedff;color:#5348c9;text-align:left;font-weight:800}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}}tr:last-child td{{border-bottom:0}}td small{{display:block;color:#8790a0;font-size:12px}}code{{font-family:Consolas,"SFMono-Regular",monospace;font-size:12px;background:#f0f2f6;border-radius:4px;padding:2px 5px;color:#344157}}.hash{{max-width:280px;word-break:break-all}}.hash code{{background:none;padding:0;color:#56637a}}.jar-list{{font-size:12px;line-height:1.45;word-break:break-all}}.state{{display:inline-flex;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:700}}.state.ok{{background:#e5f7f0;color:#168267}}.state.missing{{background:#fff0d9;color:#b56a16}}
.role-dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px}}.role-dot.blue,.coverage-bar i.blue{{background:#5a50db}}.role-dot.purple,.coverage-bar i.purple{{background:#835fd0}}.role-dot.green,.coverage-bar i.green{{background:#1ba17f}}.role-dot.teal,.coverage-bar i.teal{{background:#249ba4}}.role-dot.orange,.coverage-bar i.orange{{background:#e28c32}}.role-dot.gray,.coverage-bar i.gray{{background:#8b95a4}}.coverage-bar{{height:8px;min-width:120px;background:#f0f1f4;border-radius:99px;overflow:hidden;margin-top:5px}}.coverage-bar i{{display:block;height:100%;border-radius:inherit}}
.search-panel{{padding:20px}}.search-top{{display:flex;gap:10px;align-items:center;margin-bottom:12px}}.search-input{{flex:1;min-width:0;padding:11px 13px;border:1px solid #cfd2dc;border-radius:9px;background:#fff;color:var(--ink);font:inherit;outline:none}}.search-input:focus{{border-color:#6559dd;box-shadow:0 0 0 3px #e9e7ff}}.result-count{{white-space:nowrap;color:#7c8494;font-size:12px}}.filters{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:16px}}.filter{{border:1px solid #ddddea;background:#fafafe;color:#626b7c;border-radius:999px;padding:4px 11px;cursor:pointer;font:inherit;font-size:12px}}.filter.active{{background:#eeecff;border-color:#bdb7fa;color:#4f43c5;font-weight:700}}.search-grid{{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,.72fr);gap:14px}}.results{{display:grid;gap:8px;align-content:start;max-height:640px;overflow:auto;padding-right:4px}}.result{{text-align:left;border:1px solid #e1e1e8;background:#fff;border-radius:10px;padding:10px 12px;cursor:pointer;color:var(--ink)}}.result:hover,.result.selected{{border-color:#8e84ee;box-shadow:0 4px 12px rgba(81,70,201,.1)}}.result-name{{font-weight:800;color:#29335a;overflow-wrap:anywhere}}.result-meta{{color:#7a8494;font-size:12px;margin-top:2px}}.result .role-text{{font-weight:700}}.detail{{border:1px solid #e1e1e8;border-radius:10px;background:#fbfbfd;min-height:180px;max-height:640px;overflow:auto;padding:15px}}.detail h3{{margin:0 0 4px;font-size:17px;overflow-wrap:anywhere}}.detail-meta{{color:#747e90;font-size:12px;margin-bottom:10px}}.detail pre{{white-space:pre-wrap;word-break:break-word;margin:12px 0 0;background:#f1f2f6;border-radius:8px;padding:11px;font:12px/1.55 Consolas,"SFMono-Regular",monospace;color:#344157}}.empty{{color:#8a92a0;padding:20px;text-align:center}}
.bottom-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.info-card{{padding:18px 20px}}.info-card h3{{margin:0 0 8px;font-size:16px}}.info-card ul{{padding-left:20px;margin:8px 0 0;color:#667185}}.footer{{color:#8b92a0;text-align:center;font-size:12px;margin-top:28px}}a{{color:#5146c9;text-decoration:none}}a:hover{{text-decoration:underline}}
@media(max-width:850px){{.stats{{grid-template-columns:repeat(2,1fr)}}.search-grid,.bottom-grid{{grid-template-columns:1fr}}.search-top{{align-items:stretch;flex-direction:column}}.result-count{{align-self:flex-end}}h1{{font-size:28px}}.panel{{overflow-x:auto}}table{{min-width:760px}}}}
</style></head><body><div class="page">
<header class="hero"><div class="eyebrow">PORTABLE SLAY THE SPIRE AI KNOWLEDGE PACK</div><h1>Slay the Spire {html.escape(game_version)} · 完整 Mod API 知识报告</h1><p>真实 Java/JAR 元数据、继承关系、重载签名、注解、字段和资源索引；JSON/JSONL 是事实来源，本页面用于浏览、检索和核对。</p><div class="badges">{badge_html}</div></header>
<section class="stats">{stat_cards}</section>
<div class="callout"><strong>分析边界：</strong>本报告按生成时本机的 `desktop-1.0.jar`、ModTheSpire、BaseMod、StSLib 与已安装 Mod 生成；当前 Steam Workshop API 分类的 {api_library_present}/{len(WORKSHOP_API_IDS)} 个项目也已纳入并在下方单独列出。API 记录保留私有成员、真实 JVM 描述符和方法代码哈希；本包不复制游戏二进制和图片，版本变化后应先用 SHA-256 校验并重新生成。</div>

<section class="section"><h2 class="section-title">一、版本与文件指纹 <span>当前资料基线</span></h2><div class="panel"><table><thead><tr><th>角色</th><th>程序/文件</th><th>大小</th><th>SHA-256</th><th>元数据版本</th></tr></thead><tbody>{fingerprint_html}</tbody></table><div class="panel-pad" style="color:#778092;font-size:12px">JAR 快照共 {number(len(jar_inventory))} 个：本体 {base_jar_count}、框架 {framework_count}、本地 Mod {local_count}、Workshop Mod {workshop_count}。其中框架 JAR 来自 Workshop，但在报告中单独归类；完整清单见 <code>environment/jar_inventory.jsonl</code> 与 <code>environment/workshop_manifest.json</code>。</div></div></section>

<section class="section" id="libraries"><h2 class="section-title">二、依赖库与框架清单 <span>{api_library_present}/{len(WORKSHOP_API_IDS)} 个 Workshop API 项目</span></h2><div class="panel"><table><thead><tr><th>分类</th><th>库/框架</th><th>实际 JAR</th><th>声明依赖</th><th>类型</th><th>状态</th></tr></thead><tbody>{api_library_html}</tbody></table><div class="panel-pad" style="color:#778092;font-size:12px">这里按 Steam Workshop 的 API 分类记录专用库、框架和可复用前置；其他普通内容 Mod 仍完整收录在 <code>api/installed_mods_api.types.jsonl</code> 与 <code>environment/mod_catalog.json</code>。同名 JAR 按 portable_path 区分。</div></div></section>

<section class="section"><h2 class="section-title">三、API 覆盖统计 <span>{number(total_types)} 个可索引类型</span></h2><div class="panel"><table><thead><tr><th>资料角色</th><th>类型</th><th>方法</th><th>字段</th><th>占比</th></tr></thead><tbody>{coverage_html}</tbody></table></div></section>

<section class="section" id="search"><h2 class="section-title">四、完整 API 搜索 <span>类名、包名、方法、字段、注解和 JAR</span></h2><div class="panel search-panel"><div class="search-top"><input id="q" class="search-input" placeholder="搜索 AbstractCard、BaseMod.addCard、SpirePatch、receive... 或来源 JAR"><span id="resultCount" class="result-count"></span></div><div id="filters" class="filters"></div><div class="search-grid"><div id="results" class="results"></div><div id="detail" class="detail"><div class="empty">点击左侧类型查看继承关系、成员索引和可复制的查询命令。</div></div></div></div></section>

<section class="section bottom-grid"><div class="panel info-card"><h3>给 AI 的推荐读取顺序</h3><ul><li>先读本报告和 <code>manifest.json</code>，确认 JAR 指纹。</li><li>本体查 <code>api/base_game_api.types.jsonl</code>；编译/补丁查 ModTheSpire、BaseMod、StSLib 分卷。</li><li>遇到资源、版本和加载问题，查 <code>environment/</code> 与 <code>resources/</code>。</li></ul></div><div class="panel info-card"><h3>配套工具</h3><ul><li><code>tools/query-sts-api.ps1</code>：脚本查询完整签名。</li><li><code>tools/verify-sts-pack.ps1</code>：校验本机 JAR 与整包文件。</li><li><code>tools/javap-type.ps1</code>：按需查看当前类的 Java/字节码输出。</li></ul></div></section>
<div class="footer">离线报告 · 当前 JAR 快照 · {number(len(jar_inventory))} 个 JAR · {number(resource_count)} 个资源索引 · <a href="#search">回到 API 搜索</a></div>
</div>
<script>
const DATA={payload};const ROLE_META={role_json};let activeRole='all';let selected=null;
const q=document.getElementById('q'),results=document.getElementById('results'),detail=document.getElementById('detail'),filters=document.getElementById('filters'),resultCount=document.getElementById('resultCount');
const roleOrder=['all','base_game','modthespire','basemod','stslib','installed_mods','third_party'];
function label(role){{return role==='all'?'全部':((ROLE_META[role]||{{}}).short||role)}}
for(const role of roleOrder){{const b=document.createElement('button');b.className='filter'+(role==='all'?' active':'');b.textContent=label(role);b.dataset.role=role;b.onclick=()=>{{activeRole=role;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x.dataset.role===role));render()}};filters.appendChild(b)}}
function searchable(x){{return [x.full_name,x.package,x.role,x.source_jar,x.super_type,...(x.method_names||[]),...(x.field_names||[]),...(x.annotation_types||[])].join(' ').toLowerCase()}}
function showDetail(x,button){{selected=x;document.querySelectorAll('.result').forEach(y=>y.classList.remove('selected'));if(button)button.classList.add('selected');const meta=ROLE_META[x.role]||{{label:x.role}};detail.innerHTML='';const h=document.createElement('h3');h.textContent=x.full_name;detail.appendChild(h);const m=document.createElement('div');m.className='detail-meta';m.textContent=meta.label+' · '+x.source_jar+' · '+(x.super_type||'无父类')+' · '+x.method_count+' methods · '+x.field_count+' fields';detail.appendChild(m);const p=document.createElement('div');p.textContent='接口：'+((x.interfaces||[]).join(', ')||'无')+'\\n注解：'+((x.annotation_types||[]).join(', ')||'无')+'\\n\\nPowerShell 查询：\\n.\\\\tools\\\\query-sts-api.ps1 -PackRoot $PWD -Role '+x.role+' -TypeName "'+x.full_name+'"';detail.appendChild(p);const pre=document.createElement('pre');pre.textContent=JSON.stringify(x,null,2);detail.appendChild(pre)}}
function render(){{const term=q.value.trim().toLowerCase();let hits=DATA.filter(x=>(activeRole==='all'||x.role===activeRole)&&(!term||searchable(x).includes(term)));resultCount.textContent=hits.length.toLocaleString()+' 个结果';results.innerHTML='';if(!hits.length){{results.innerHTML='<div class="empty">没有匹配。尝试完整类名、短类名、方法名或切换资料角色。</div>';detail.innerHTML='<div class="empty">无选中类型。</div>';return}}for(const x of hits.slice(0,250)){{const b=document.createElement('button');b.className='result';const n=document.createElement('div');n.className='result-name';n.textContent=x.full_name;b.appendChild(n);const meta=document.createElement('div');meta.className='result-meta';const role=ROLE_META[x.role]||{{short:x.role}};meta.innerHTML='<span class="role-text">'+role.short+'</span> · '+x.source_jar+' · '+x.method_count+' 方法 · '+x.field_count+' 字段';b.appendChild(meta);b.onclick=()=>showDetail(x,b);results.appendChild(b)}}if(selected&&hits.includes(selected))showDetail(selected,Array.from(results.children).find(b=>b.querySelector('.result-name')?.textContent===selected.full_name))}}
q.addEventListener('input',render);render();
</script></body></html>'''
    (root / "sts_ai_knowledge_report.html").write_text(report, encoding="utf-8")


def ignored_index_path(relative_path: str) -> bool:
    path = relative_path.replace("\\", "/")
    parts = path.split("/")
    return (
        not path
        or path == "ai_file_index.jsonl"
        or parts[0] in INDEX_IGNORED_ROOTS
        or path.startswith("templates/build/")
        or path.endswith(".pyc")
    )


def ai_file_metadata(relative_path: str) -> Dict[str, Any]:
    """Return machine-readable ingestion policy for one generated pack file."""
    path = relative_path.replace("\\", "/")
    parse_as = "text"
    role = "supporting_text"
    include_by_default = False
    priority = 3
    notes = "按需读取；先确认对应版本和任务范围。"

    if path in {"AI_INGESTION_GUIDE.md", "ai_manifest.json", "manifest.json", "README.md"}:
        role = "ingestion_instructions"
        include_by_default = True
        priority = 1
        notes = "默认入口和版本边界。"
        parse_as = "json" if path.endswith(".json") else "text"
    elif path == "CHANGELOG.md":
        role = "release_history"
        priority = 5
        notes = "仅在需要追踪知识包变更时读取。"
    elif path.startswith("api/"):
        if path.endswith(".manifest.json"):
            role = "api_provenance_manifest"
            include_by_default = True
            priority = 1
            parse_as = "json"
            notes = "API 来源 JAR、记录数和覆盖范围。"
        elif path.endswith(".index.json"):
            role = "api_lookup_index"
            include_by_default = True
            priority = 1
            parse_as = "json"
            notes = "用于按类型名快速定位 JSONL 记录。"
        elif path.endswith(".types.jsonl"):
            role_name = Path(path).name.removesuffix("_api.types.jsonl")
            role = "canonical_api_signatures" if role_name in DEFAULT_API_ROLES else "optional_api_records"
            include_by_default = role_name in DEFAULT_API_ROLES
            priority = 1 if include_by_default else 3
            parse_as = "jsonl"
            notes = (
                "当前游戏/框架 API；只在任务涉及该角色时读取。"
                if include_by_default
                else "大体量已安装 Mod 或第三方 API；只按目标类型/成员查询，不要整文件加载。"
            )
    elif path.startswith("environment/"):
        role = "environment_fingerprint" if path.endswith(".json") else "environment_records"
        include_by_default = path.endswith(".json")
        priority = 2 if include_by_default else 3
        parse_as = "json" if path.endswith(".json") else "jsonl"
        notes = (
            "版本、路径和摘要指纹；用于确认当前安装是否匹配。"
            if include_by_default
            else "逐条查询的环境记录；版本问题或资源/补丁定位时按需读取。"
        )
    elif path.startswith("docs/"):
        role = "modding_instructions"
        include_by_default = True
        priority = 1
        notes = "面向 Mod 开发、补丁、资源和排错的说明。"
    elif path.startswith("templates/"):
        role = "build_template"
        include_by_default = True
        priority = 2
        parse_as = "source_text" if Path(path).suffix.lower() in {".java", ".ps1"} else "text"
        notes = "创建和编译最小 Java 8 Mod 的模板文件。"
    elif path.startswith("tools/"):
        role = "verification_tool"
        include_by_default = True
        priority = 2
        parse_as = "source_text"
        notes = "按需执行的查询、验证和再生成工具。"
    elif path.startswith("bytecode/"):
        if path == "bytecode/README.md":
            role = "bytecode_instructions"
            include_by_default = True
            priority = 2
            notes = "解释补丁目标和 JVM 指令快照的使用边界。"
        else:
            role = "bytecode_records" if path.endswith(".jsonl") else "bytecode_reference"
            priority = 3
            parse_as = "jsonl" if path.endswith(".jsonl") else "text"
            if path == "bytecode/full_game_instruction_snapshots.jsonl":
                notes = "Complete parsed JVM instruction records for every base-game API method; query by class and method on demand."
            elif path == "bytecode/full_game_parse_errors.jsonl":
                notes = "Audit list of base-game class parse errors; an empty file means no parse errors were observed."
            notes = "补丁目标行为核对资料；只读取命中的类/方法。"
    elif path.startswith("resources/"):
        role = "resource_records"
        priority = 3
        parse_as = "jsonl"
        notes = "JAR 内文本资源和本地化索引；按资源路径查询。"
    elif path.endswith(".html"):
        role = "human_report"
        priority = 5
        notes = "供人工浏览；不作为 AI 默认事实来源。"

    return {
        "optional": not include_by_default,
        "include_by_default": include_by_default,
        "role": role,
        "priority": priority,
        "parse_as": parse_as,
        "notes": notes,
    }


def write_ai_manifest(
    root: Path,
    generated_at_utc: str,
    game_version: str,
    jar_inventory: List[Dict[str, Any]],
    counts: Dict[str, Dict[str, int]],
    java_info: Dict[str, Any],
    bytecode_summary: Dict[str, Any],
    external_summary: Dict[str, Any],
) -> None:
    base = next((j for j in jar_inventory if j.get("name") == "desktop-1.0.jar"), {})
    frameworks = {
        item["name"]: {
            "portable_path": item.get("portable_path"),
            "sha256": item.get("sha256"),
            "workshop_id": item.get("workshop_id"),
        }
        for item in jar_inventory
        if item.get("scope") == "framework"
    }
    scope_counts = Counter(str(item.get("scope")) for item in jar_inventory)
    payload = {
        "schema_version": AI_MANIFEST_SCHEMA,
        "pack_id": "slay-the-spire-ai-modding-knowledge-ai-ready",
        "pack_version": PACK_VERSION,
        "generated_at_utc": generated_at_utc,
        "source_pack_id": "slay-the-spire-ai-modding-knowledge",
        "source_pack_version": PACK_VERSION,
        "game": {
            "app_id": "646570",
            "version": game_version,
            "base_jar": base.get("name"),
            "base_jar_sha256": base.get("sha256"),
        },
        "runtime": {
            "java": java_info,
            "javap_version": bytecode_summary.get("javap_version"),
            "frameworks": frameworks,
        },
        "coverage": {
            "jar_count": len(jar_inventory),
            "jar_scope_counts": dict(sorted(scope_counts.items())),
            "api_counts": {role: dict(sorted(data.items())) for role, data in sorted(counts.items())},
            "workshop_external_files": {
                "file_count": external_summary.get("file_count", 0),
                "total_bytes": external_summary.get("total_bytes", 0),
            },
            "patch_targets": {
                "patch_reference_count": bytecode_summary.get("patch_reference_count", 0),
                "instruction_snapshot_count": bytecode_summary.get("instruction_snapshot_count", 0),
                "javap_snapshot_count": bytecode_summary.get("javap_snapshot_count", 0),
            },
            "full_base_game_bytecode": {
                "class_count": bytecode_summary.get("full_game_class_count", 0),
                "parsed_class_count": bytecode_summary.get("full_game_parsed_class_count", 0),
                "parse_error_count": bytecode_summary.get("full_game_parse_error_count", 0),
                "method_count": bytecode_summary.get("full_game_method_count", 0),
                "methods_with_code": bytecode_summary.get("full_game_methods_with_code", 0),
                "instruction_count": bytecode_summary.get("full_game_instruction_count", 0),
            },
        },
        "canonical_roots": ["api", "environment", "bytecode", "resources", "docs", "templates", "tools"],
        "ingestion_order": [
            "AI_INGESTION_GUIDE.md",
            "ai_manifest.json",
            "manifest.json",
            "environment/*.json",
            "api/*.manifest.json",
            "api/*.index.json",
            "api/base_game_api.types.jsonl",
            "api/modthespire_api.types.jsonl",
            "api/basemod_api.types.jsonl",
            "api/stslib_api.types.jsonl",
            "docs/*.md",
            "bytecode/README.md",
            "templates/*",
            "tools/*",
        ],
        "precedence": {
            "current_api": "api/*.types.jsonl and matching API manifest",
            "version_truth": "environment/jar_inventory.jsonl plus tools/verify-sts-pack.ps1 output",
            "runtime_truth": "current ModTheSpire/game logs and current build output at user-provided paths",
            "behavior_evidence": "full base-game JVM instruction snapshot plus targeted javap/patch records; revalidate after JAR hash changes",
            "archive": "installed_mods, third_party, resources, bytecode records and HTML report are on-demand",
        },
        "default_files": [
            "AI_INGESTION_GUIDE.md",
            "ai_manifest.json",
            "manifest.json",
            "README.md",
            "api/*.manifest.json",
            "api/*.index.json",
            "api/base_game_api.types.jsonl",
            "api/modthespire_api.types.jsonl",
            "api/basemod_api.types.jsonl",
            "api/stslib_api.types.jsonl",
            "environment/*.json",
            "docs/*.md",
            "bytecode/README.md",
            "templates/*",
            "tools/*",
        ],
        "on_demand_files": [
            "api/installed_mods_api.types.jsonl",
            "api/third_party_api.types.jsonl",
            "environment/*.jsonl",
            "bytecode/*.jsonl",
            "bytecode/javap/*",
            "resources/text_resources.jsonl",
            "sts_ai_knowledge_report.html",
        ],
        "not_default_ingestion": [
            "ai_file_index.jsonl",
            "templates/build/**",
            "**/*.pyc",
            ".git/**",
        ],
        "notes": [
            "Default AI ingestion is intentionally curated; large JSONL datasets must be queried by role, type, member, or path.",
            "The complete factual inventory remains present even when a file is marked on-demand.",
            "The pack does not copy game/Mod binaries or Workshop external file bytes; it stores signatures, paths and hashes.",
            "path_at_generation is audit-only; use portable_path and verify current JAR hashes before relying on signatures.",
            "The complete base-game JVM instruction snapshot covers parsed com.megacrit.cardcrawl.* methods; third-party and installed-mod bytecode remains represented by API signatures and targeted patch evidence.",
        ],
    }
    (root / "ai_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_template(root: Path) -> None:
    template = root / "templates"
    source = template / "src" / "main" / "java" / "example"
    source.mkdir(parents=True, exist_ok=True)
    (template / "ModTheSpire.json").write_text(json.dumps({
        "modid": "MinimalStsMod", "name": "Minimal StS Mod", "author_list": ["YourName"],
        "description": "Minimal Java 8 ModTheSpire/BaseMod template.", "version": "0.1.0",
        "dependencies": ["basemod"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (source / "MinimalMod.java").write_text("""package example;

import basemod.BaseMod;
import basemod.interfaces.PostInitializeSubscriber;
import com.evacipated.cardcrawl.modthespire.lib.SpireInitializer;

@SpireInitializer
public class MinimalMod implements PostInitializeSubscriber {
    public MinimalMod() {
        BaseMod.subscribe(this);
    }

    public static void initialize() {
        new MinimalMod();
    }

    @Override
    public void receivePostInitialize() {
        // Register cards, relics, strings, or UI here after the base game is initialized.
    }
}
""", encoding="utf-8")
    (template / "build.ps1").write_text(r'''[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$StsRoot,
    [Parameter(Mandatory = $true)] [string]$JavaHome,
    [string]$ModTheSpireJar,
    [string]$BaseModJar,
    [string]$StSLibJar,
    [string]$OutputJar = (Join-Path $PSScriptRoot 'MinimalStsMod.jar')
)
$ErrorActionPreference = 'Stop'
$StsRoot = [IO.Path]::GetFullPath($StsRoot)
$JavaHome = [IO.Path]::GetFullPath($JavaHome)
$steamapps = Split-Path (Split-Path $StsRoot)
$workshopRoot = Join-Path $steamapps 'workshop\content\646570'
if (-not $ModTheSpireJar) { $ModTheSpireJar = (Get-ChildItem $workshopRoot -Filter ModTheSpire.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
if (-not $BaseModJar) { $BaseModJar = (Get-ChildItem $workshopRoot -Filter BaseMod.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
if (-not $StSLibJar) { $StSLibJar = (Get-ChildItem $workshopRoot -Filter StSLib.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
$javac = Join-Path $JavaHome 'bin\javac.exe'
$jar = Join-Path $JavaHome 'bin\jar.exe'
$required = @($javac, $jar, (Join-Path $StsRoot 'desktop-1.0.jar'), $ModTheSpireJar, $BaseModJar)
foreach ($file in $required) { if (-not $file -or -not (Test-Path -LiteralPath $file)) { throw "Missing build input: $file" } }
$classes = Join-Path $PSScriptRoot 'build\classes'
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$cp = @((Join-Path $StsRoot 'desktop-1.0.jar'), $ModTheSpireJar, $BaseModJar, $StSLibJar) -join [IO.Path]::PathSeparator
$sources = Get-ChildItem (Join-Path $PSScriptRoot 'src\main\java') -Filter *.java -Recurse | Select-Object -ExpandProperty FullName
& $javac -encoding UTF-8 -source 8 -target 8 -cp $cp -d $classes $sources
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ModTheSpire.json') -Destination $classes -Force
& $jar cf $OutputJar -C $classes .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Built $OutputJar"
''', encoding="utf-8")
    (template / "README.md").write_text("""# Minimal StS Mod 模板

这是 Java 8 + ModTheSpire + BaseMod 的最小入口。模板不复制任何游戏或框架 JAR；用 `build.ps1` 通过参数指向本机安装。

```powershell
.\\build.ps1 `
  -StsRoot 'E:\\SteamLibrary\\steamapps\\common\\SlayTheSpire' `
  -JavaHome 'C:\\Program Files\\Java\\jdk8'
```

如果多个创意工坊版本同时存在，显式传 `-ModTheSpireJar`、`-BaseModJar`、`-StSLibJar`。运行时需要把生成的 JAR 和根目录 `ModTheSpire.json` 放进 ModTheSpire 扫描的模组目录；实际加载顺序和错误以当前启动日志为准。
""", encoding="utf-8")


def build_pack(args: argparse.Namespace) -> None:
    game_root = Path(args.game_root).expanduser().resolve()
    local_mods = Path(args.local_mods or game_root / "mods").expanduser().resolve()
    workshop_root = Path(args.workshop_root or game_root.parent.parent / "workshop" / "content" / "646570").expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"output is non-empty; use --force to rebuild: {output}")
    output.mkdir(parents=True, exist_ok=True)
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    for directory in [output / "api", output / "environment", output / "docs", output / "templates", output / "tools", output / "resources"]:
        directory.mkdir(parents=True, exist_ok=True)

    specs = discover_jars(game_root, local_mods, workshop_root)
    if not specs or not (game_root / "desktop-1.0.jar").is_file():
        raise SystemExit(f"desktop-1.0.jar not found under {game_root}")
    game_version = detect_game_version(game_root / "desktop-1.0.jar") or "unknown"
    roots = [("game", game_root), ("local_mods", local_mods), ("workshop", workshop_root)]

    api_handles: Dict[str, Any] = {}
    api_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"types": 0, "methods": 0, "fields": 0, "bytes": 0})
    api_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    patch_references: List[Dict[str, Any]] = []
    class_locations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    all_index_path = output / "environment" / "class_index.jsonl"
    all_index = all_index_path.open("w", encoding="utf-8")
    jar_inventory: List[Dict[str, Any]] = []
    catalog: List[Dict[str, Any]] = []
    resource_text_handle = (output / "resources" / "text_resources.jsonl").open("w", encoding="utf-8")
    resource_inventory_handle = (output / "environment" / "resource_inventory.jsonl").open("w", encoding="utf-8")

    def handle_for(role: str):
        if role not in api_handles:
            api_handles[role] = (output / "api" / ROLE_FILES[role]).open("w", encoding="utf-8")
        return api_handles[role]

    try:
        for spec in specs:
            path: Path = spec["path"]
            print(f"[scan] {path.name}", flush=True)
            jar_hash = sha256_file(path)
            text_entries: List[Dict[str, Any]] = []
            summaries: List[Dict[str, Any]] = []
            role_counts: Counter[str] = Counter()
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                metadata_name, metadata, metadata_candidates, metadata_status, metadata_raw_fallback = read_mod_metadata(zf)
                manifest = {}
                if "META-INF/MANIFEST.MF" in zf.namelist():
                    manifest = parse_manifest(zf.read("META-INF/MANIFEST.MF"))
                class_names = [n for n in names if n.endswith(".class") and not n.startswith("META-INF/versions/")]
                resource_entries = []
                for info in zf.infolist():
                    if info.is_dir() or info.filename.startswith("META-INF/") or info.filename.endswith(".class"):
                        continue
                    entry = {
                        "source_jar": path.name,
                        "source_jar_portable_path": spec["portable_path"],
                        "workshop_id": spec["workshop_id"],
                        "resource_path": info.filename,
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                        "crc32": f"{info.CRC:08X}",
                        "extension": Path(info.filename).suffix.lower(),
                    }
                    resource_entries.append(entry)
                    if Path(info.filename).suffix.lower() in TEXT_SUFFIXES:
                        raw = zf.read(info.filename)
                        preview = text_preview(raw)
                        if preview is not None:
                            text_entries.append({**entry, "text": preview, "json": safe_json(raw)})

                for class_name in class_names:
                    try:
                        record = parse_class(zf.read(class_name))
                    except Exception as exc:  # keep the inventory useful for unusual classes
                        record = {
                            "schema_version": SCHEMA,
                            "full_name": class_name[:-6].replace("/", "."),
                            "name": Path(class_name[:-6]).name,
                            "package": class_name[:-6].replace("/", ".").rpartition(".")[0],
                            "kind": "unparsed",
                            "parse_error": str(exc),
                            "fields": [], "methods": [], "interfaces": [],
                            "annotations": [], "inner_classes": [],
                        }
                    full_name = record["full_name"]
                    role = classify_role(spec, full_name)
                    record["assembly_role"] = role
                    record["source_jar"] = path.name
                    record["source_jar_portable_path"] = spec["portable_path"]
                    record["workshop_id"] = spec["workshop_id"]
                    handle = handle_for(role)
                    line = api_counts[role]["types"] + 1
                    encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                    handle.write(encoded + "\n")
                    api_counts[role]["types"] += 1
                    api_counts[role]["methods"] += len(record.get("methods", []))
                    api_counts[role]["fields"] += len(record.get("fields", []))
                    api_counts[role]["bytes"] += len(encoded.encode("utf-8")) + 1
                    role_counts[role] += 1
                    summary = class_summary(record, spec, role, line)
                    summaries.append(summary)
                    api_index[role].append(summary)
                    all_index.write(json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n")
                    class_locations[full_name].append({"spec": spec, "entry": class_name})
                    patch_references.extend(patch_targets_from_record(record, spec))

                for item in text_entries:
                    resource_text_handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

                spec_record = {
                    "name": path.name,
                    "scope": spec["scope"],
                    "workshop_id": spec["workshop_id"],
                    "portable_path": spec["portable_path"],
                    "path_at_generation": str(path),
                    "size": path.stat().st_size,
                    "sha256": jar_hash,
                    "class_count": len(class_names),
                    "resource_count": len(resource_entries),
                    "role_counts": dict(sorted(role_counts.items())),
                    "manifest": manifest,
                    "mod_metadata_file": metadata_name,
                    "metadata_candidates": metadata_candidates,
                    "metadata_status": metadata_status,
                    "metadata_raw_fallback": metadata_raw_fallback,
                    "metadata": metadata,
                    "resource_paths": [x["resource_path"] for x in resource_entries],
                    "resource_text_count": len(text_entries),
                }
                jar_inventory.append(spec_record)
                catalog.append({
                    "jar_name": path.name,
                    "scope": spec["scope"],
                    "workshop_id": spec["workshop_id"],
                    "portable_path": spec["portable_path"],
                    "sha256": jar_hash,
                    "metadata_file": metadata_name,
                    "metadata_status": metadata_status,
                    "metadata_raw_fallback": metadata_raw_fallback,
                    "metadata": metadata,
                    "class_count": len(class_names),
                    "role_counts": dict(sorted(role_counts.items())),
                    "packages": sorted(set(s["package"] for s in summaries if s["package"])),
                    "resource_roots": sorted(set(p.split("/", 1)[0] for p in [x["resource_path"] for x in resource_entries] if p)),
                    **mod_candidates(summaries),
                })
                for item in resource_entries:
                    resource_inventory_handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    finally:
        for handle in api_handles.values():
            handle.close()
        all_index.close()
        resource_text_handle.close()
        resource_inventory_handle.close()

    java_info: Dict[str, Any] = {"version": "not-run", "path": None}
    java_candidates = [
        game_root / "jre" / "bin" / "java.exe",
        game_root / "jre" / "bin" / "java",
        Path("java"),
    ]
    for java in java_candidates:
        try:
            proc = subprocess.run([str(java), "-version"], capture_output=True, text=True, timeout=10)
            output_text = (proc.stderr or proc.stdout).strip()
            if output_text:
                java_info = {"path": str(java), "version": output_text.splitlines()[0]}
                break
        except (OSError, subprocess.SubprocessError):
            continue

    (output / "environment" / "jar_inventory.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in jar_inventory) + "\n",
        encoding="utf-8",
    )
    (output / "environment" / "mod_catalog.json").write_text(json.dumps({
        "schema_version": SCHEMA, "generated_at_utc": generated_at_utc,
        "mods": catalog,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    acf_path = workshop_root.parent.parent / "appworkshop_646570.acf"
    acf_data: Dict[str, Any] = {}
    acf_file: Dict[str, Any] = {"path_at_generation": str(acf_path), "exists": acf_path.is_file()}
    if acf_path.is_file():
        acf_file.update({"size": acf_path.stat().st_size, "sha256": sha256_file(acf_path)})
        acf_data = parse_vdf(acf_path.read_text(encoding="utf-8", errors="replace"))
    (output / "environment" / "workshop_manifest.json").write_text(json.dumps({
        "schema_version": SCHEMA, "generated_at_utc": generated_at_utc, "app_id": "646570", "acf_file": acf_file,
        "installed_workshop_ids": sorted(set(j["workshop_id"] for j in jar_inventory if j.get("workshop_id"))),
        "acf": acf_data,
        "note": "The ACF is an audit snapshot; the local JAR path and SHA-256 remain authoritative when verifying a pack.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    external_files, external_summary = inventory_workshop_external_files(workshop_root)
    (output / "environment" / "workshop_external_files.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in external_files) + "\n",
        encoding="utf-8",
    )
    (output / "environment" / "workshop_external_summary.json").write_text(
        json.dumps({"schema_version": SCHEMA, **external_summary}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    bytecode_summary = generate_bytecode_artifacts(
        output, patch_references, class_locations, specs,
        Path(args.javap_home).expanduser().resolve() if args.javap_home else None,
    )

    for role, filename in ROLE_FILES.items():
        entries = api_index.get(role, [])
        (output / "api" / filename.replace(".types.jsonl", ".index.json")).write_text(json.dumps({
            "schema_version": SCHEMA, "role": role, "type_file": filename,
            "type_count": len(entries), "method_count": api_counts[role]["methods"], "field_count": api_counts[role]["fields"],
            "types": entries,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "api" / filename.replace(".types.jsonl", ".manifest.json")).write_text(json.dumps({
            "schema_version": SCHEMA, "role": role, "type_file": f"api/{filename}",
            "type_count": api_counts[role]["types"], "method_count": api_counts[role]["methods"],
            "field_count": api_counts[role]["fields"], "record_bytes": api_counts[role]["bytes"],
            "source_jars": sorted(set(e["source_jar"] for e in entries)),
            "coverage": "all parsed class files assigned to this role; fields and methods include non-public members",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (output / "environment" / "environment_manifest.json").write_text(json.dumps({
        "schema_version": SCHEMA,
        "generated_at_utc": generated_at_utc,
        "os": platform.platform(),
        "python": sys.version,
        "game_root_at_generation": str(game_root),
        "local_mods_at_generation": str(local_mods),
        "workshop_root_at_generation": str(workshop_root),
        "game_app_id": "646570",
        "java": java_info,
        "javap_home_at_generation": str(Path(args.javap_home).expanduser().resolve()) if args.javap_home else None,
        "framework_jars": sorted(FRAMEWORK_JARS),
        "api_parser": "generate_sts_pack.py / JVM class-file parser",
        "notes": [
            "Portable consumers should use portable_path and role; path_at_generation is audit-only.",
            "The base game API role is limited to com.megacrit.cardcrawl.*; bundled libraries are in third_party.",
            "Installed mod APIs include local mods and workshop jars present at generation time.",
            "Workshop external files are indexed by path, size, and SHA-256; their binary contents are not copied.",
            "Patch target records include raw annotation targets, javap snapshots, and parsed JVM bytecode instructions when available.",
            "Invalid ModTheSpire.json files retain a metadata_raw_fallback field instead of being silently discarded.",
        ],
        "workshop_external_files": {
            "manifest": "environment/workshop_external_files.jsonl",
            "summary": "environment/workshop_external_summary.json",
            "file_count": external_summary["file_count"],
            "total_bytes": external_summary["total_bytes"],
        },
        "patch_targets": bytecode_summary,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    generate_docs(output, api_counts, jar_inventory, catalog, java_info, game_root, generated_at_utc, bytecode_summary)
    write_query_tool(output)
    write_verify_tool(output)
    write_javap_tool(output)
    write_bytecode_query_tool(output)
    write_html_report(output, api_counts, api_index, jar_inventory, game_version)
    write_template(output)
    write_ai_manifest(
        output,
        generated_at_utc,
        game_version,
        jar_inventory,
        api_counts,
        java_info,
        bytecode_summary,
        external_summary,
    )
    generator_copy = output / "tools" / "generate_sts_pack.py"
    if Path(__file__).resolve() != generator_copy.resolve():
        shutil.copy2(Path(__file__).resolve(), generator_copy)

    manifest = {
        "schema_version": SCHEMA,
        "pack_id": "slay-the-spire-ai-modding-knowledge",
        "pack_version": PACK_VERSION,
        "generated_by": f"generate_sts_pack.py/{PACK_VERSION}",
        "generated_at_utc": generated_at_utc,
        "purpose": "Portable Slay the Spire Java ModTheSpire/BaseMod/StSLib mod-development knowledge pack",
        "game_profile": {
            "app_id": "646570",
            "game_version": game_version,
            "game_version_source": "com/megacrit/cardcrawl/core/CardCrawlGame.class",
            "base_jar": "desktop-1.0.jar",
            "base_jar_sha256": next((j["sha256"] for j in jar_inventory if j["name"] == "desktop-1.0.jar"), None),
        },
        "roles": ROLE_FILES,
        "portability_rules": [
            "Use portable_path and role; never depend on path_at_generation.",
            "Accept a source JAR only when environment/jar_inventory.jsonl SHA-256 matches.",
            "Keep base_game, ModTheSpire, BaseMod, StSLib, installed_mods, and third_party API files separate.",
            "Do not infer method overloads from names; use descriptor and parameter_types.",
        ],
        "jars": jar_inventory,
        "workshop_external_files": external_summary,
        "patch_target_artifacts": bytecode_summary,
        "files": [
            "AI_INGESTION_GUIDE.md", "ai_manifest.json", "manifest.json", "ai_file_index.jsonl",
            "environment/", "api/", "bytecode/", "docs/", "templates/", "tools/", "resources/",
        ],
        "file_index_policy": {
            "file": "ai_file_index.jsonl",
            "excluded_paths": [".git/**", ".hg/**", ".svn/**", "__pycache__/**", "templates/build/**", "**/*.pyc"],
            "note": "VCS metadata, Python caches and template build output are not knowledge-pack content.",
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Index every generated file after all files have been created.
    index_path = output / "ai_file_index.jsonl"
    with index_path.open("w", encoding="utf-8") as index:
        for file in sorted(p for p in output.rglob("*") if p.is_file()):
            relative = file.relative_to(output).as_posix()
            if ignored_index_path(relative):
                continue
            index.write(json.dumps({
                "path": relative,
                **ai_file_metadata(relative),
                "size": file.stat().st_size,
                "sha256": sha256_file(file),
            }, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps({
        "output": str(output),
        "jars": len(jar_inventory),
        "api_counts": {k: dict(v) for k, v in sorted(api_counts.items())},
        "catalog_mods": len(catalog),
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True)
    parser.add_argument("--local-mods")
    parser.add_argument("--workshop-root")
    parser.add_argument("--javap-home", help="Optional JDK home used to capture javap -p -s -c snapshots")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    build_pack(parser.parse_args())


if __name__ == "__main__":
    main()

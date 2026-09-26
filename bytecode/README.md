# 补丁目标字节码快照

`environment/patch_targets.jsonl` records which installed Mod patch annotations point to which target classes/methods.

`instruction_snapshots.jsonl` contains parsed JVM instructions, offsets, operands, constant-pool references, branch targets, and method bytecode hashes. `javap/` contains the corresponding `javap -p -s -c` text snapshots when a JDK tool was available at generation time.

Slay the Spire is a Java game, so these are JVM bytecode instructions (Java IL equivalent), not .NET CLR IL. Missing classes or methods remain recorded with an explicit status instead of being guessed.

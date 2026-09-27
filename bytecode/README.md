# 补丁目标字节码快照

`environment/patch_targets.jsonl` records which installed Mod patch annotations point to which target classes/methods.

`full_game_instruction_snapshots.jsonl` contains the parsed JVM instructions for every method in the current `base_game` API namespace (`com.megacrit.cardcrawl.*`). It is the complete base-game method-level bytecode snapshot for this JAR baseline and is intended for on-demand class/method queries.

`instruction_snapshots.jsonl` is the smaller patch-target-focused snapshot. It contains parsed JVM instructions, offsets, operands, constant-pool references, branch targets, and method bytecode hashes. `javap/` contains the corresponding `javap -p -s -c` text snapshots when a JDK tool was available at generation time.

`full_game_parse_errors.jsonl` is an explicit audit list for any base-game class that could not be parsed; an empty file means no parse errors were observed.

Slay the Spire is a Java game, so these are JVM bytecode instructions (Java IL equivalent), not .NET CLR IL. Missing patch classes or methods remain recorded with an explicit status instead of being guessed.

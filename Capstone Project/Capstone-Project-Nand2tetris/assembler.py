import re
import sys

K = 15                  # your K
FEATURE = K % 3         # 15 % 3 = 0 -> duplicate label warning

COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}
JUMP = {"": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
        "JLT": "100", "JLE": "110", "JNE": "101", "JMP": "111"}

PREDEFINED = {f"R{i}": i for i in range(16)}
PREDEFINED.update({"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
                   "SCREEN": 16384, "KBD": 24576})

SYMBOL_OK = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


def clean(line):
    """Remove comments and all spaces."""
    return "".join(line.split("//")[0].split())


def c_instruction(n, text):
    dest, jump, comp = "", "", text
    if "=" in comp:
        dest, comp = comp.split("=", 1)
    if ";" in comp:
        comp, jump = comp.split(";", 1)

    if comp not in COMP:                      # allow A+D, M|D, etc.
        for op in "+&|":
            if op in comp:
                left, right = comp.split(op, 1)
                if right + op + left in COMP:
                    comp = right + op + left
    if comp not in COMP:
        raise ValueError(f"Line {n}: invalid instruction '{text}' (bad comp)")
    if jump not in JUMP:
        raise ValueError(f"Line {n}: invalid instruction '{text}' (bad jump)")
    if dest and (set(dest) - set("AMD") or len(set(dest)) != len(dest)):
        raise ValueError(f"Line {n}: invalid instruction '{text}' (bad dest)")

    d = ("1" if "A" in dest else "0") + ("1" if "D" in dest else "0") + \
        ("1" if "M" in dest else "0")
    return "111" + COMP[comp] + d + JUMP[jump]


def assemble(path):
    # ---- read & clean ----
    with open(path) as f:
        lines = [(n, clean(raw)) for n, raw in enumerate(f.read().splitlines(), 1)]
    lines = [(n, t) for n, t in lines if t]

    # ---- FIRST PASS: find labels ----
    symbols = dict(PREDEFINED)
    labels, count = {}, 0
    for n, t in lines:
        if t.startswith("("):
            if not t.endswith(")") or len(t) < 3:
                raise ValueError(f"Line {n}: invalid label '{t}'")
            name = t[1:-1]
            if name in labels:
                if FEATURE == 2:
                    print(f"Warning: Line {n}: label ({name}) is defined twice")
            else:
                labels[name] = count
        else:
            count += 1
    symbols.update(labels)

    # ---- SECOND PASS: translate ----
    variables, next_var, out = {}, 16, []
    for n, t in lines:
        if t.startswith("("):
            continue
        if t.startswith("@"):
            s = t[1:]
            if s.isdigit():
                val = int(s)
                if val > 32767:
                    raise ValueError(f"Line {n}: invalid instruction '{t}' (number too big)")
            elif SYMBOL_OK.match(s):
                if s not in symbols:
                    symbols[s] = variables[s] = next_var
                    next_var += 1
                val = symbols[s]
            else:
                raise ValueError(f"Line {n}: invalid instruction '{t}'")
            out.append(format(val, "016b"))
        else:
            out.append(c_instruction(n, t))
    return out, labels, variables


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py Prog.asm")
        sys.exit(1)
    src = sys.argv[1]
    dst = src.rsplit(".", 1)[0] + ".hack"
    try:
        code, labels, variables = assemble(src)
    except ValueError as e:
        if FEATURE == 1:
            print(e)
            sys.exit(1)
        raise
    with open(dst, "w") as f:
        f.write("\n".join(code) + "\n")
    if FEATURE == 0:
        with open("symbols.txt", "w") as f:
            for name, addr in {**labels, **variables}.items():
                f.write(f"{name} {addr}\n")
    print(f"Wrote {dst} ({len(code)} instructions)")


main()
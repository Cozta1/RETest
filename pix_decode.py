#!/usr/bin/env python3
"""
Decodificador de PIX "copia e cola" (BR Code / EMV MPM).
Uso:
    python3 pix_decode.py "00020126...6304ABCD"
    echo "0002..." | python3 pix_decode.py

NÃO faz nenhuma conexão de rede. Só interpreta o texto do PIX,
revelando o recebedor (chave, nome, cidade), o valor e o txid.
Rode com -I para isolar de imports locais: python3 -I pix_decode.py "<codigo>"
"""
import sys

# Rótulos dos campos EMV mais relevantes para análise forense de PIX
TOP = {
    "00": "Payload Format Indicator",
    "01": "Point of Initiation (11=estatico/reutilizavel, 12=dinamico/uso unico)",
    "26": "Merchant Account Information - PIX",
    "52": "Merchant Category Code (MCC)",
    "53": "Moeda (986=BRL)",
    "54": "Valor da transacao (R$)",
    "58": "Pais",
    "59": "Nome do recebedor",
    "60": "Cidade do recebedor",
    "61": "CEP",
    "62": "Dados adicionais (ex.: txid)",
    "63": "CRC16",
}
PIX_SUB = {  # dentro do campo 26 (ou 26-51, GUIs de pagamento)
    "00": "GUI (br.gov.bcb.pix)",
    "01": "Chave PIX (recebedor)",
    "02": "Descricao",
    "25": "URL do payload dinamico (PSP/gateway)",
}
SUB62 = {"05": "txid (referencia)", "01": "referencia"}


def parse(s, labels=None, depth=0):
    out = []
    i = 0
    while i + 4 <= len(s):
        tag = s[i:i + 2]
        try:
            ln = int(s[i + 2:i + 4])
        except ValueError:
            break
        val = s[i + 4:i + 4 + ln]
        out.append((tag, ln, val))
        i += 4 + ln
    for tag, ln, val in out:
        name = (labels or {}).get(tag, "")
        pad = "  " * depth
        print(f"{pad}[{tag}] {name}: {val!r}")
        if tag == "26":
            parse(val, PIX_SUB, depth + 1)
        elif tag == "62":
            parse(val, SUB62, depth + 1)
    return out


def crc16(payload: str) -> str:
    crc = 0xFFFF
    for ch in payload.encode("utf-8"):
        crc ^= ch << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def main():
    code = (sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()).strip()
    # Remove apenas quebras de linha/tab; NUNCA espacos internos (contam no TLV)
    for ch in ("\n", "\r", "\t"):
        code = code.replace(ch, "")
    if not code:
        print("Cole o PIX copia-e-cola como argumento.", file=sys.stderr)
        sys.exit(1)
    print(f"Tamanho: {len(code)} chars\n--- Campos ---")
    parse(code, TOP)
    # valida CRC: tudo menos os 4 digitos finais, incluindo '6304'
    if code[-8:-4] == "6304":
        base = code[:-4]
        calc = crc16(base)
        got = code[-4:].upper()
        print(f"\nCRC16 informado={got} calculado={calc} -> {'OK' if calc == got else 'DIVERGENTE'}")
    print("\nRESUMO FORENSE:")
    fields = {t: v for t, _, v in parse_quiet(code)}
    print("  Tipo       :", "dinamico/uso unico" if fields.get("01") == "12" else fields.get("01", "?"))
    print("  Valor      :", fields.get("54", "(nao fixado no codigo)"))
    print("  Nome receb.:", fields.get("59", "?"))
    print("  Cidade     :", fields.get("60", "?"))
    sub = {t: v for t, _, v in parse_quiet(fields.get("26", ""))}
    print("  Chave PIX  :", sub.get("01", "(ausente; provavel PIX dinamico via PSP)"))
    print("  URL PSP    :", sub.get("25", "(nenhuma)"))


def parse_quiet(s):
    out, i = [], 0
    while i + 4 <= len(s):
        tag = s[i:i + 2]
        try:
            ln = int(s[i + 2:i + 4])
        except ValueError:
            break
        out.append((tag, ln, s[i + 4:i + 4 + ln]))
        i += 4 + ln
    return out


if __name__ == "__main__":
    main()

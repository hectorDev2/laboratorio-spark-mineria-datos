"""Funciones puras para la composición del informe."""


def format_count(value):
    return f"{int(value):,}".replace(",", " ")


def format_pct(value):
    return f"{float(value) * 100:.2f} %".replace(".", ",")

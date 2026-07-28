"""
Módulo de cálculo numerológico cabalístico.

Faz a conta de verdade (determinística, sempre correta) e devolve os
números prontos. A IA generativa NUNCA calcula — ela só recebe os
números já calculados aqui e escreve a interpretação em cima deles.

Tabela usada: correspondência cabalística cíclica de 1 a 9 (a mais usada
no mercado de numerologia cabalística brasileiro). Se você já trabalha
com uma tabela diferente (ex: gematria hebraica direta, ou outra
correspondência), me avisa que eu troco só o dicionário TABELA abaixo —
o resto do código não muda.
"""

import unicodedata

TABELA = {
    "A": 1, "J": 1, "S": 1,
    "B": 2, "K": 2, "T": 2,
    "C": 3, "L": 3, "U": 3,
    "D": 4, "M": 4, "V": 4,
    "E": 5, "N": 5, "W": 5,
    "F": 6, "O": 6, "X": 6,
    "G": 7, "P": 7, "Y": 7,
    "H": 8, "Q": 8, "Z": 8,
    "I": 9, "R": 9,
}

VOGAIS = set("AEIOU")
NUMEROS_MESTRES = {11, 22, 33}


def _remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _somente_letras(nome: str) -> str:
    limpo = _remover_acentos(nome.upper())
    return "".join(c for c in limpo if c.isalpha())


def reduzir(numero: int) -> int:
    """Reduz a um dígito único, preservando números mestres (11, 22, 33)."""
    while numero > 9 and numero not in NUMEROS_MESTRES:
        numero = sum(int(d) for d in str(numero))
    return numero


def numero_expressao(nome_completo: str) -> int:
    """Soma de todas as letras do nome — o número da expressão/destino do nome."""
    letras = _somente_letras(nome_completo)
    total = sum(TABELA[letra] for letra in letras)
    return reduzir(total)


def numero_alma(nome_completo: str) -> int:
    """Soma apenas das vogais — o número da alma / motivação."""
    letras = _somente_letras(nome_completo)
    total = sum(TABELA[letra] for letra in letras if letra in VOGAIS)
    return reduzir(total)


def numero_personalidade(nome_completo: str) -> int:
    """Soma apenas das consoantes — o número da personalidade externa."""
    letras = _somente_letras(nome_completo)
    total = sum(TABELA[letra] for letra in letras if letra not in VOGAIS)
    return reduzir(total)


def numero_caminho_de_vida(data_nascimento: str) -> int:
    """
    Soma de todos os dígitos da data de nascimento — o caminho de vida.
    Espera data no formato DD/MM/AAAA.
    """
    digitos = [int(c) for c in data_nascimento if c.isdigit()]
    total = sum(digitos)
    return reduzir(total)


ARCANJOS = {
    1: "Miguel",
    2: "Gabriel",
    3: "Rafael",
    4: "Uriel",
    5: "Camael",
    6: "Zadquiel",
    7: "Haniel",
    8: "Cassiel",
    9: "Samael",
    11: "Jofiel",
    22: "Metatron",
    33: "Sandalfon",
}


def arcanjo_pessoal(nome_completo: str) -> str:
    """
    Determina o arcanjo pessoal com base no número da alma — determinístico,
    sempre o mesmo resultado para o mesmo nome (não é a IA quem escolhe).
    """
    numero = numero_alma(nome_completo)
    return ARCANJOS[numero]


def calcular_mapa(nome_completo: str, data_nascimento: str) -> dict:
    """Retorna todos os números calculados para o nome e data informados."""
    return {
        "numero_expressao": numero_expressao(nome_completo),
        "numero_alma": numero_alma(nome_completo),
        "numero_personalidade": numero_personalidade(nome_completo),
        "numero_caminho_de_vida": numero_caminho_de_vida(data_nascimento),
        "arcanjo_pessoal": arcanjo_pessoal(nome_completo),
    }


if __name__ == "__main__":
    # Teste rápido
    mapa = calcular_mapa("Maria Fernanda Souza", "14/03/1991")
    for chave, valor in mapa.items():
        print(f"{chave}: {valor}")

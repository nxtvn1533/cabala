"""
Pipeline completo: recebe os dados do cliente (vindos do webhook da Leona),
chama a API do ChatGPT com o prompt-mestre, gera o PDF personalizado
e devolve o caminho do arquivo pronto para envio.

Requer: pip install openai --break-system-packages
Requer: variável de ambiente OPENAI_API_KEY configurada no servidor
"""

import os
import json
import subprocess
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader

from numerologia import calcular_mapa  # cálculo determinístico, sem IA

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])  # timeout/retries abaixo

# Cole aqui o conteúdo do prompt-mestre (system prompt) que já validamos
with open("prompt_mestre.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def gerar_leitura(nome: str, data_nascimento: str, plano: str, tentativas: int = 3) -> dict:
    """
    Calcula os números (Python, determinístico) e chama a API do ChatGPT
    só para escrever a interpretação em cima desses números já prontos.

    Tenta novamente automaticamente (até 3x) se a API falhar ou demorar —
    importante quando vários clientes pedem ao mesmo tempo.
    """
    numeros = calcular_mapa(nome, data_nascimento)

    payload_usuario = json.dumps({
        "nome": nome,
        "data_nascimento": data_nascimento,
        "plano": plano,
        "numeros_calculados": numeros,  # a IA usa esses valores, não calcula
    }, ensure_ascii=False)

    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.chat.completions.create(
                model="gpt-4.1",  # ou o modelo que você preferir usar
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload_usuario}
                ],
                response_format={"type": "json_object"},  # força saída em JSON válido
                temperature=0.8,
                timeout=30,  # não deixa uma chamada travada seguntar o worker
            )
            texto_json = resposta.choices[0].message.content
            return json.loads(texto_json)

        except Exception as erro:
            ultimo_erro = erro
            print(f"[tentativa {tentativa}/{tentativas}] falhou: {erro}")

    # Se todas as tentativas falharem, o erro sobe pro endpoint da API,
    # que devolve um erro 500 — a Leona pode tratar isso avisando o cliente
    # que algo deu errado e pra tentar de novo em instantes.
    raise ultimo_erro


def montar_pdf(dados: dict, nome_arquivo: str, template_dir: str = ".") -> str:
    """Recebe o JSON da leitura e gera o PDF final usando o template."""
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("template_carta_antiga.html")

    html_renderizado = template.render(
        capa=dados["capa"],
        secoes=dados["secoes"],
        mensagem_de_encerramento=dados.get(
            "mensagem_de_encerramento",
            "Que essa leitura ilumine seus próximos passos."
        )
    )

    html_temp = f"{nome_arquivo}.html"
    with open(html_temp, "w", encoding="utf-8") as f:
        f.write(html_renderizado)

    caminho_pdf = f"{nome_arquivo}.pdf"
    subprocess.run([
        "wkhtmltopdf",
        "--enable-local-file-access",
        "--page-size", "A4",
        "--margin-top", "0", "--margin-bottom", "0",
        "--margin-left", "0", "--margin-right", "0",
        html_temp, caminho_pdf
    ], check=True)

    return caminho_pdf


def montar_mensagem_whatsapp(dados: dict) -> str:
    """
    Formata o JSON da leitura como texto para envio direto no chat.
    Usa a formatação nativa do WhatsApp: *negrito*, _itálico_.
    """
    linhas = []
    linhas.append(f"✦ *{dados['capa']['titulo_personalizado']}* ✦")
    linhas.append(f"_Para: {dados['capa']['nome']}_")
    linhas.append("")

    for secao in dados["secoes"]:
        linhas.append(f"*{secao['titulo']}*")
        linhas.append(secao["conteudo"])
        linhas.append("")  # linha em branco entre seções

    linhas.append(dados.get(
        "mensagem_de_encerramento",
        "Que essa leitura ilumine seus próximos passos."
    ))

    return "\n".join(linhas)


def processar_pedido(nome: str, data_nascimento: str, plano: str, telefone: str) -> dict:
    """
    Função principal chamada pelo webhook da Leona.

    Retorna um dicionário com "tipo" ("texto" ou "pdf") para que a Leona
    saiba se deve mandar uma mensagem de chat normal ou anexar um arquivo:

    - Plano básico  -> {"tipo": "texto", "conteudo": "..."}
    - Essencial/Premium -> {"tipo": "pdf", "caminho_pdf": "..."}
    """
    dados = gerar_leitura(nome, data_nascimento, plano)

    if plano == "basico":
        mensagem = montar_mensagem_whatsapp(dados)
        return {"tipo": "texto", "conteudo": mensagem}

    # essencial e premium seguem para PDF
    nome_arquivo = f"mapa_{telefone}_{plano}"
    caminho_pdf = montar_pdf(dados, nome_arquivo)
    return {"tipo": "pdf", "caminho_pdf": caminho_pdf}


if __name__ == "__main__":
    # Teste local — troque "plano" para testar os três cenários
    resultado = processar_pedido(
        nome="Maria Fernanda Souza",
        data_nascimento="14/03/1991",
        plano="essencial",
        telefone="5511999999999"
    )
    print(resultado)

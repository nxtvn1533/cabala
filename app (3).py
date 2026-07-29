"""
API que a Leona vai chamar via HTTP Request para gerar a leitura
e receber de volta o que precisa enviar ao cliente.

Instalação:
    pip install fastapi uvicorn openai jinja2 --break-system-packages

Rodar localmente para testar:
    uvicorn app:app --host 0.0.0.0 --port 8000

Endpoint que a Leona vai chamar:
    POST /gerar-leitura

    Body (JSON) — jeito preferido, manda o JSON cru que o Bloco de IA
    da Leona devolveu, sem precisar quebrar em sub-campos:
        {
          "dados_cliente": "{\"nome_completo\": \"...\", \"data_nascimento\": \"...\"}",
          "plano": "...",
          "telefone": "..."
        }

    Body (JSON) — jeito alternativo, com campos já separados:
        { "nome": "...", "data_nascimento": "...", "plano": "...", "telefone": "..." }

    Resposta quando plano = "basico":
        { "tipo": "texto", "conteudo": "✦ *Mapa...* texto formatado pro WhatsApp" }

    Resposta quando plano = "essencial" ou "premium":
        { "tipo": "pdf", "pdf_url": "https://seu-dominio.com/arquivos/mapa_....pdf" }

    Na Leona, depois de chamar esse endpoint, você ramifica o fluxo:
    - Se "tipo" == "texto"  -> nó de "enviar mensagem de texto", usando {{conteudo}}
    - Se "tipo" == "pdf"    -> nó de "enviar documento/mídia", usando {{pdf_url}}
"""

import os
import json
import uuid
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline_completo import processar_pedido  # reaproveita o que já criamos

app = FastAPI()

# Pasta pública onde os PDFs ficam disponíveis por link direto
os.makedirs("arquivos_publicos", exist_ok=True)
app.mount("/arquivos", StaticFiles(directory="arquivos_publicos"), name="arquivos")

# Troque pelo domínio real onde esse backend vai ficar hospedado
DOMINIO_BASE = os.environ.get("DOMINIO_BASE", "https://seu-dominio.com")


class PedidoLeitura(BaseModel):
    # Jeito 1 (preferido): manda o JSON cru que a IA da Leona devolveu,
    # sem depender da Leona quebrar isso em sub-campos (que se mostrou instável).
    dados_cliente: str | None = None  # ex: {"nome_completo": "...", "data_nascimento": "..."}

    # Jeito 2 (alternativo): manda os campos já separados, se preferir.
    nome: str | None = None
    data_nascimento: str | None = None

    plano: str  # "basico" | "essencial" | "premium"
    telefone: str = "cliente"  # opcional — usado só pra nomear o arquivo

    def extrair_nome_e_data(self) -> tuple[str, str]:
        """
        Resolve nome e data de nascimento. Tenta, em ordem:
        1. dados_cliente como JSON válido
        2. dados_cliente no formato "objeto solto" da Leona
           (ex: {nome_completo:Fulano,data_nascimento:20/09/1997} — sem aspas)
        3. campos nome/data_nascimento enviados diretamente
        """
        if self.dados_cliente:
            texto = self.dados_cliente.strip()

            # remove blocos de código markdown, caso a IA tenha envolvido o JSON em ```json ... ```
            if texto.startswith("```"):
                texto = texto.strip("`")
                if texto.lower().startswith("json"):
                    texto = texto[4:]
                texto = texto.strip()

            # Tentativa 1: JSON válido de verdade
            try:
                dados = json.loads(texto)
                return dados["nome_completo"], dados["data_nascimento"]
            except json.JSONDecodeError:
                pass

            # Tentativa 2: formato "objeto solto" da Leona, sem aspas
            # ex: {nome_completo:Fulano de Tal,data_nascimento:20/09/1997}
            miolo = texto.strip()
            if miolo.startswith("{") and miolo.endswith("}"):
                miolo = miolo[1:-1]

            campos = {}
            for pedaco in miolo.split(","):
                if ":" not in pedaco:
                    continue
                chave, valor = pedaco.split(":", 1)
                campos[chave.strip()] = valor.strip()

            if "nome_completo" in campos and "data_nascimento" in campos:
                return campos["nome_completo"], campos["data_nascimento"]

            raise ValueError(f"Não foi possível extrair nome/data de: {texto!r}")

        if self.nome and self.data_nascimento:
            return self.nome, self.data_nascimento

        raise ValueError("Nenhum dado de nome/data foi enviado (nem dados_cliente, nem nome+data_nascimento)")


@app.post("/gerar-leitura")
def gerar_leitura_endpoint(pedido: PedidoLeitura):
    try:
        nome, data_nascimento = pedido.extrair_nome_e_data()

        resultado = processar_pedido(
            nome=nome,
            data_nascimento=data_nascimento,
            plano=pedido.plano,
            telefone=pedido.telefone,
        )

        # Plano básico: devolve o texto pronto, sem gerar arquivo
        if resultado["tipo"] == "texto":
            return {"tipo": "texto", "conteudo": resultado["conteudo"]}

        # Essencial/Premium: move o PDF pra pasta pública e devolve o link
        # Nome do arquivo PREVISÍVEL (telefone + plano, sem código aleatório).
        # Isso permite que a Leona monte a URL do documento usando só {numero}
        # numa URL fixa, sem precisar mapear "pdf_url" da resposta (que se
        # mostrou instável de referenciar corretamente na plataforma).
        nome_arquivo_final = f"mapa_{pedido.telefone}_{pedido.plano}.pdf"
        destino = os.path.join("arquivos_publicos", nome_arquivo_final)
        os.replace(resultado["caminho_pdf"], destino)

        # Também salva uma cópia com nome FIXO por plano (sem telefone).
        # Isso permite que o nó "Enviar documento" da Leona use uma URL
        # 100% estática — sem nenhuma variável — contornando o bug de
        # substituição de variável que só acontece nesse campo específico.
        # Atenção: se dois clientes comprarem o mesmo plano ao mesmo tempo,
        # essa cópia fixa pode ser sobrescrita antes da entrega — é um
        # contorno temporário, não a solução definitiva.
        nome_fixo = f"ultimo_{pedido.plano}.pdf"
        destino_fixo = os.path.join("arquivos_publicos", nome_fixo)
        shutil.copyfile(destino, destino_fixo)

        pdf_url = f"{DOMINIO_BASE}/arquivos/{nome_arquivo_final}"
        return {"tipo": "pdf", "pdf_url": pdf_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
def status():
    return {"ok": True}


@app.get("/debug-arquivos")
def debug_arquivos():
    """
    Endpoint temporário de depuração: lista os PDFs realmente salvos no
    servidor, com o nome exato de cada arquivo. Útil pra conferir se o
    {numero} da Leona está batendo com o telefone real, ou se está vindo
    diferente/vazio.
    """
    arquivos = sorted(os.listdir("arquivos_publicos"))
    return {"total": len(arquivos), "arquivos": arquivos}

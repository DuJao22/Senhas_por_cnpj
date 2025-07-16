from flask import Flask, render_template
import sqlitecloud
import sqlite3    # Mantido por compatibilidade: sqlitecloud espelha a API do sqlite3
import os

app = Flask(__name__)

# String de conexão SQLite Cloud
DATABASE_URL = (
    "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/"
    "savi_dados_unificado.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"
)

# ---------- Regras de validação por convênio ----------
VALIDACAO_PROCEDIMENTOS = {
    "Hapvida": [
        "PSICOTERAPIA TEA",
        "TERAPIA OCUPACIONAL TEA",
        "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA",
        "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA",
    ],
    "Notredame": [
        "PSICOTERAPIA TEA",
        "TERAPIA OCUPACIONAL TEA",
        "FONOAUDIOLOGIA TEA",
        "CONSULTA/SESSAO PSICOPEDAGOGIA - TEA",
        "SESSAO DE FISIOTERAPIA PARA TEA",
        "SESSAO MUSICOTERAPIA",
    ],
    "Hapvida_neuro": [
        "TESTE NEUROPSICOLOGICO",
        "CONSULTA/SESSAO DE NEUROPSICOLOGIA",
    ],
    "Notredame_neuro": [
        "TESTE NEUROPSICOLOGICO",
        "CONSULTA/SESSAO DE NEUROPSICOLOGIA",
    ],
    "Hapvida_libelula": ["CONSULTA EM CONSULTORIO"],
    "Notredame_libelula": ["CONSULTA EM CONSULTORIO"],
}

# ---------- Conexão ----------
def get_connection():
    """Devolve uma nova conexão com o SQLite Cloud."""
    return sqlitecloud.connect(DATABASE_URL)


# ---------- Validação ----------
def validar_procedimento(empresa, procedimento_nome):
    """Valida se o procedimento é permitido para a empresa."""
    return procedimento_nome in VALIDACAO_PROCEDIMENTOS.get(empresa, [])


# ---------- Análise de dados ----------
def analisar_dados():
    """Retorna a lista de registros com inconsistências."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se a tabela existe
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='producao'
            """
        )
        if not cursor.fetchone():
            conn.close()
            return [], "Tabela 'producao' não encontrada no banco de dados."

        # Buscar todos os registros
        cursor.execute(
            """
            SELECT usuario_nome, numero_guia, data_execucao, empresa, procedimento_nome
            FROM producao
            ORDER BY data_execucao DESC
            """
        )
        registros = cursor.fetchall()
        conn.close()

        # Filtrar inconsistências
        erros = [
            {
                "usuario_nome": u,
                "numero_guia": g,
                "data_execucao": d,
                "empresa": e,
                "procedimento_nome": p,
                "procedimentos_permitidos": VALIDACAO_PROCEDIMENTOS.get(e, []),
            }
            for u, g, d, e, p in registros
            if not validar_procedimento(e, p)
        ]
        return erros, None

    except sqlite3.Error as e:  # sqlitecloud mantém a hierarquia de exceções
        return [], f"Erro ao acessar o banco de dados: {e}"
    except Exception as e:
        return [], f"Erro inesperado: {e}"


# ---------- Rotas ----------
@app.route("/")
def index():
    """Página inicial."""
    return render_template("index.html", validacao_regras=VALIDACAO_PROCEDIMENTOS)


@app.route("/erros")
def relatorio_erros():
    """Mostra o relatório de inconsistências."""
    erros, erro_msg = analisar_dados()

    estatisticas = {}
    if erros:
        empresas_erros = {}
        procedimentos_erros = {}
        for erro in erros:
            empresas_erros[erro["empresa"]] = empresas_erros.get(erro["empresa"], 0) + 1
            procedimentos_erros[erro["procedimento_nome"]] = (
                procedimentos_erros.get(erro["procedimento_nome"], 0) + 1
            )

        estatisticas = {
            "total_erros": len(erros),
            "empresas_afetadas": len(empresas_erros),
            "procedimentos_unicos": len(procedimentos_erros),
            "empresas_erros": empresas_erros,
            "procedimentos_erros": procedimentos_erros,
        }

    return render_template(
        "erros.html",
        erros=erros,
        erro_msg=erro_msg,
        estatisticas=estatisticas,
        validacao_regras=VALIDACAO_PROCEDIMENTOS,
    )


@app.route("/status")
def status_banco():
    """Exibe informações gerais do banco."""
    info = {
        "conexao_ok": False,
        "tabela_existe": False,
        "total_registros": 0,
        "empresas_encontradas": [],
        "erro": None,
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()
        info["conexao_ok"] = True

        # Tabela produzida?
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='producao'
            """
        )
        info["tabela_existe"] = cursor.fetchone() is not None

        if info["tabela_existe"]:
            cursor.execute("SELECT COUNT(*) FROM producao")
            info["total_registros"] = cursor.fetchone()[0]

            cursor.execute("SELECT DISTINCT empresa FROM producao ORDER BY empresa")
            info["empresas_encontradas"] = [row[0] for row in cursor.fetchall()]

        conn.close()

    except sqlite3.Error as e:
        info["erro"] = f"Erro ao acessar o banco: {e}"
    except Exception as e:
        info["erro"] = f"Erro inesperado: {e}"

    return render_template("status.html", info=info)


# ---------- Execução ----------
if __name__ == "__main__":
    app.run(debug=True)

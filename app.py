from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)

# Configuração do banco de dados
DATABASE = 'savi_dados_unificado.db'

# Regras de validação por convênio
VALIDACAO_PROCEDIMENTOS = {
    'Hapvida': [
        'PSICOTERAPIA TEA',
        'TERAPIA OCUPACIONAL TEA',
        'FONOAUDIOLOGIA TEA',
        'CONSULTA/SESSAO PSICOPEDAGOGIA - TEA',
        'SESSAO DE FISIOTERAPIA PARA TEA',
        'SESSAO MUSICOTERAPIA'
    ],
    'Notredame': [
        'PSICOTERAPIA TEA',
        'TERAPIA OCUPACIONAL TEA',
        'FONOAUDIOLOGIA TEA',
        'CONSULTA/SESSAO PSICOPEDAGOGIA - TEA',
        'SESSAO DE FISIOTERAPIA PARA TEA',
        'SESSAO MUSICOTERAPIA'
    ],
    'Hapvida_neuro': [
        'TESTE NEUROPSICOLOGICO',
        'CONSULTA/SESSAO DE NEUROPSICOLOGIA'
    ],
    'Notredame_neuro': [
        'TESTE NEUROPSICOLOGICO',
        'CONSULTA/SESSAO DE NEUROPSICOLOGIA'
    ],
    'Hapvida_libelula': [
        'CONSULTA EM CONSULTORIO'
    ],
    'Notredame_libelula': [
        'CONSULTA EM CONSULTORIO'
    ]
}

def validar_procedimento(empresa, procedimento_nome):
    """Valida se o procedimento é permitido para a empresa"""
    if empresa in VALIDACAO_PROCEDIMENTOS:
        return procedimento_nome in VALIDACAO_PROCEDIMENTOS[empresa]
    return False

def analisar_dados():
    """Analisa os dados da tabela producao e retorna registros com erros"""
    if not os.path.exists(DATABASE):
        return [], f"Banco de dados '{DATABASE}' não encontrado."
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='producao'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return [], "Tabela 'producao' não encontrada no banco de dados."
        
        # Buscar todos os registros da tabela producao
        cursor.execute("""
            SELECT usuario_nome, numero_guia, data_execucao, empresa, procedimento_nome
            FROM producao
            ORDER BY data_execucao DESC
        """)
        
        registros = cursor.fetchall()
        conn.close()
        
        # Filtrar apenas os registros com erros
        erros = []
        for registro in registros:
            usuario_nome, numero_guia, data_execucao, empresa, procedimento_nome = registro
            
            if not validar_procedimento(empresa, procedimento_nome):
                erros.append({
                    'usuario_nome': usuario_nome,
                    'numero_guia': numero_guia,
                    'data_execucao': data_execucao,
                    'empresa': empresa,
                    'procedimento_nome': procedimento_nome,
                    'procedimentos_permitidos': VALIDACAO_PROCEDIMENTOS.get(empresa, [])
                })
        
        return erros, None
        
    except sqlite3.Error as e:
        return [], f"Erro ao acessar o banco de dados: {str(e)}"
    except Exception as e:
        return [], f"Erro inesperado: {str(e)}"

@app.route('/')
def index():
    """Página inicial com informações do sistema"""
    return render_template('index.html', validacao_regras=VALIDACAO_PROCEDIMENTOS)

@app.route('/erros')
def relatorio_erros():
    """Página com análise de erros dos dados existentes"""
    erros, erro_msg = analisar_dados()
    
    # Estatísticas dos erros
    estatisticas = {}
    if erros:
        # Contar erros por empresa
        empresas_erros = {}
        procedimentos_erros = {}
        
        for erro in erros:
            empresa = erro['empresa']
            procedimento = erro['procedimento_nome']
            
            empresas_erros[empresa] = empresas_erros.get(empresa, 0) + 1
            procedimentos_erros[procedimento] = procedimentos_erros.get(procedimento, 0) + 1
        
        estatisticas = {
            'total_erros': len(erros),
            'empresas_afetadas': len(empresas_erros),
            'procedimentos_unicos': len(procedimentos_erros),
            'empresas_erros': empresas_erros,
            'procedimentos_erros': procedimentos_erros
        }
    
    return render_template('erros.html', 
                         erros=erros, 
                         erro_msg=erro_msg,
                         estatisticas=estatisticas,
                         validacao_regras=VALIDACAO_PROCEDIMENTOS)

@app.route('/status')
def status_banco():
    """Página com informações sobre o status do banco de dados"""
    info = {
        'banco_existe': os.path.exists(DATABASE),
        'caminho_banco': os.path.abspath(DATABASE),
        'tabela_existe': False,
        'total_registros': 0,
        'empresas_encontradas': [],
        'erro': None
    }
    
    if info['banco_existe']:
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='producao'
            """)
            
            info['tabela_existe'] = cursor.fetchone() is not None
            
            if info['tabela_existe']:
                # Contar registros
                cursor.execute("SELECT COUNT(*) FROM producao")
                info['total_registros'] = cursor.fetchone()[0]
                
                # Listar empresas únicas
                cursor.execute("SELECT DISTINCT empresa FROM producao ORDER BY empresa")
                info['empresas_encontradas'] = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
        except sqlite3.Error as e:
            info['erro'] = f"Erro ao acessar o banco: {str(e)}"
        except Exception as e:
            info['erro'] = f"Erro inesperado: {str(e)}"
    
    return render_template('status.html', info=info)

if __name__ == '__main__':
    app.run(debug=True)

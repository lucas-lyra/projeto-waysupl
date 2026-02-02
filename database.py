import sqlite3
import pandas as pd
import hashlib

def conectar():
    """Cria conexão com o banco de dados SQLite."""
    conn = sqlite3.connect("way_suplementos.db")
    return conn

def criar_tabelas():
    """Cria as tabelas necessárias se elas não existirem."""
    conn = conectar()
    cursor = conn.cursor()

    # 1. Tabela de Filiais
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS filiais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL
    )
    """)

    # 2. Tabela de Usuários (Logins e Senhas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        nivel TEXT DEFAULT 'operador' -- admin ou operador
    )
    """)

    # 3. Tabela de Produtos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filial_id INTEGER,
        codigo_barras TEXT,
        nome TEXT NOT NULL,
        marca TEXT,
        validade DATE,
        quantidade INTEGER DEFAULT 0,
        observacoes TEXT,
        FOREIGN KEY (filial_id) REFERENCES filiais (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def hash_senha(senha: str) -> str:
    """Criptografa a senha para não salvar em texto limpo."""
    return hashlib.sha256(senha.encode()).hexdigest()

def adicionar_usuario_padrao():
    """Adiciona um admin inicial caso a tabela esteja vazia."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        senha_adm = hash_senha("way123")
        cursor.execute("INSERT INTO usuarios (username, senha, nivel) VALUES (?, ?, ?)", 
                       ("admin", senha_adm, "admin"))
    conn.commit()
    conn.close()

# Inicializa o banco ao rodar este arquivo
if __name__ == "__main__":
    criar_tabelas()
    adicionar_usuario_padrao()
    print("Banco de dados configurado com sucesso!")
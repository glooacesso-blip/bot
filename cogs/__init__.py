        # NOVA TABELA: Configuração da Portaria
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portaria_config (
                guild_id TEXT PRIMARY KEY,
                channel_id TEXT,
                imagem_url TEXT,
                texto_custom TEXT
            )
        ''')
        self.conn.commit()

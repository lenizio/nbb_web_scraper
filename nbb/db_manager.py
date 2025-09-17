import psycopg2
from psycopg2 import sql
from psycopg2.errors import UniqueViolation, NotNullViolation, InFailedSqlTransaction
from itemadapter import ItemAdapter
import hashlib
import logging
import os
from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import OperationalError
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)

try:
    DB_CONFIG = {
        'host': os.environ['DB_HOST'],
        'database': os.environ['DB_NAME'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASS'],
        'port': os.environ.get('DB_PORT', '5432')  
    }
except KeyError as e:
    logger.critical(f"Variável de ambiente obrigatória ausente: {e}")
    raise SystemExit(f"Variável de ambiente obrigatória ausente: {e}")


try:
    POOL = ThreadedConnectionPool(minconn=1, maxconn=32, **DB_CONFIG)
    logger.info("Pool de conexões criado com sucesso.")
except OperationalError as e:
    logger.critical(f"Erro ao criar pool de conexões: {e}", exc_info=True)
    raise SystemExit(f"Não foi possível criar o pool de conexões: {e}")

def close_pool():
    """Fecha todas as conexões do pool."""
    if POOL:
        POOL.closeall()
        logger.info("Pool de conexões fechado.")


class DatabaseManager:
    """Gerencia uma única conexão e cursor de banco de dados para múltiplas operações."""
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.cur = None

    def __enter__(self):
        """Estabelece uma conexão e retorna o cursor ao entrar em um bloco 'with'."""
        try:
            self.conn = POOL.getconn()
            self.conn.autocommit = False
            self.cur = self.conn.cursor()
            return self
        except Exception as e:
            logger.error(f"Erro ao obter conexão do pool: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fecha o cursor e a conexão, confirmando ou desfazendo as alterações com base no sucesso."""
        if self.cur:
            self.cur.close()
        if self.conn:
            if exc_type is None: 
                self.conn.commit()
            else: 
                self.conn.rollback()
                logger.error(f"Transação revertida devido a uma exceção: {exc_val}", exc_info=True)
            POOL.putconn(self.conn)

    def create_tables(self):
        """
        Cria todas as tabelas necessárias se elas ainda não existirem.
        Este método é chamado uma vez em uma instância do DatabaseManager.
        """
        try:
            self.cur.execute("""
                -- Table for teams (id is PRIMARY KEY, automatically indexed)
                CREATE TABLE IF NOT EXISTS teams (
                    id VARCHAR(100) PRIMARY KEY,
                    name VARCHAR(50),
                    logo TEXT
                );
                
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    player_name VARCHAR(50),
                    -- CORREÇÃO: Coluna renomeada para 'player_icon_url' para consistência
                    player_icon_url TEXT
                );

                -- Table for player's team per season (composite PRIMARY KEY, automatically indexed)
                CREATE TABLE IF NOT EXISTS player_teams_by_season (
                    player_id INTEGER REFERENCES players(id) NOT NULL,
                    player_team_id VARCHAR(100) REFERENCES teams(id) NOT NULL,
                    season VARCHAR(20) NOT NULL,
                    player_number VARCHAR(10),
                    PRIMARY KEY (player_id, player_team_id, season)
                );
                
                -- Table for games (game_id is PRIMARY KEY, automatically indexed)
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY,
                    game_date DATE,
                    game_time TIME,
                    home_team_id VARCHAR(100) REFERENCES teams(id),
                    away_team_id VARCHAR(100) REFERENCES teams(id),
                    home_team_score INTEGER,
                    away_team_score INTEGER,
                    round VARCHAR(30),
                    stage VARCHAR(30),
                    season VARCHAR(20),
                    arena VARCHAR(100),
                    link TEXT
                );

                -- Table for player statistics in a game (composite PRIMARY KEY, automatically indexed)
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_id INTEGER REFERENCES players(id) NOT NULL,
                    game_id INTEGER REFERENCES games(id) NOT NULL,
                    team_id VARCHAR(100) REFERENCES teams(id) NOT NULL, 
                    quarter VARCHAR(10) NOT NULL, 
                    minutes_played FLOAT,
                    assist INTEGER,
                    points_attempts INTEGER,
                    points_made INTEGER,
                    defensive_rebounds INTEGER,
                    offensive_rebounds INTEGER,
                    three_points_attempts INTEGER,
                    three_points_made INTEGER,
                    two_points_attempts INTEGER,
                    two_points_made INTEGER,
                    free_throws_attempts INTEGER,
                    free_throws_made INTEGER,
                    steals INTEGER,
                    blocks INTEGER,
                    fouls_committed INTEGER,
                    fouls_received INTEGER,
                    total_errors INTEGER,
                    dunks INTEGER,
                    plus_minus_while_on_court INTEGER,
                    efficiency INTEGER,
                    PRIMARY KEY (player_id, game_id, quarter)
                );

                -- Table for shots 
                CREATE TABLE IF NOT EXISTS shots (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id),
                    game_id INTEGER REFERENCES games(id),
                    team_id VARCHAR(100) REFERENCES teams(id),
                    shot_quarter VARCHAR(10),
                    shot_time TIME,
                    shot_type VARCHAR(20),
                    shot_x_location FLOAT,
                    shot_y_location FLOAT
                );

                -- Table for play-by-play actions
                CREATE TABLE IF NOT EXISTS play_by_play (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER REFERENCES games(id) NOT NULL, 
                    player_id INTEGER REFERENCES players(id),
                    team_id VARCHAR(100) REFERENCES teams(id), 
                    quarter_time TIME,
                    quarter VARCHAR(10) NOT NULL,
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    play TEXT NOT NULL
                );
                
            """)
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}", exc_info=True)
            self.conn.rollback() 
            raise 

    def insert_team(self, team_item):
        """Insere ou atualiza um registro de equipe."""
        try:
            adapter = ItemAdapter(team_item)
            team_id = adapter.get('id')
            name = adapter.get('name')
            logo = adapter.get('logo')

            if not team_id:
                logger.warning(f"Tentativa de inserir equipe sem ID. Dados: {team_item}")
                return 

            self.cur.execute(
                """
                INSERT INTO teams (id, name, logo)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    logo = EXCLUDED.logo;
                """,
                (team_id, name, logo)
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback()
            logger.error(f"Erro ao inserir/atualizar equipe '{team_id}': {e}", exc_info=True)
            raise 
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir/atualizar equipe '{team_id}': {e}", exc_info=True)
            raise


    def insert_player(self, player_item):
        """Insere ou atualiza um registro de jogador."""
        try:
            adapter = ItemAdapter(player_item)
            player_id = adapter.get('player_id')
            player_name = adapter.get('player_name')
            player_icon_url = adapter.get('player_icon_url')

            if not player_id:
                logger.warning(f"Tentativa de inserir jogador sem ID. Dados: {player_item}")
                return

            self.cur.execute(
                """
                INSERT INTO players (id, player_name, player_icon_url)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET player_name = EXCLUDED.player_name,
                    player_icon_url = EXCLUDED.player_icon_url;
                """,
            
                (player_id, player_name, player_icon_url)
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback()
            logger.error(f"Erro ao inserir/atualizar jogador '{player_id}': {e}", exc_info=True)
            raise
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir/atualizar jogador '{player_id}': {e}", exc_info=True)
            raise

    def insert_player_team_by_season(self, player_item):
        """Insere ou atualiza o time e número de um jogador para uma temporada específica."""
        try:
            adapter = ItemAdapter(player_item)
            player_id = adapter.get('player_id')
            player_team_id = adapter.get('player_team_id')
            season = adapter.get('season')
            player_number = adapter.get('player_number')

            if not all([player_id, player_team_id, season]):
                logger.warning(f"Dados faltando para player_teams_by_season (player_id, player_team_id ou season é NULL). Dados: {player_item}")
                return

            self.cur.execute(
                """
                INSERT INTO player_teams_by_season (player_id, player_team_id, season, player_number)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, player_team_id, season) DO UPDATE 
                SET player_number = EXCLUDED.player_number;
                """,
                (player_id, player_team_id, season, player_number)
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback()
            logger.error(f"Erro ao inserir time do jogador para '{player_id}' na temporada '{season}': {e}", exc_info=True)
            raise
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir time do jogador para '{player_id}' na temporada '{season}': {e}", exc_info=True)
            raise

    def insert_game(self, game_item):
        """Insere ou atualiza um registro de jogo."""
        try:
            adapter = ItemAdapter(game_item)
            game_id = adapter.get('game_id')
            game_date = adapter.get('game_date')
            game_time = adapter.get('game_time')

            if not game_id:
                logger.warning(f"Tentativa de inserir jogo sem ID. Dados: {game_item}")
                return

            self.cur.execute(
                """
                INSERT INTO games (
                    id, game_date, game_time,
                    home_team_id, away_team_id, home_team_score, away_team_score,
                    round, stage, season, arena, link
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET game_date = EXCLUDED.game_date,
                    game_time = EXCLUDED.game_time,
                    home_team_id = EXCLUDED.home_team_id,
                    away_team_id = EXCLUDED.away_team_id,
                    home_team_score = EXCLUDED.home_team_score,
                    away_team_score = EXCLUDED.away_team_score,
                    round = EXCLUDED.round,
                    stage = EXCLUDED.stage,
                    season = EXCLUDED.season,
                    arena = EXCLUDED.arena,
                    link = EXCLUDED.link;
                """,
                
                (
                    game_id, game_date, game_time,
                    adapter.get('home_team_id'), adapter.get('away_team_id'),
                    adapter.get('home_team_score'), adapter.get('away_team_score'),
                    adapter.get('round'), adapter.get('stage'), adapter.get('season'),
                    adapter.get('arena'), adapter.get('link')
                )
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback()
            logger.error(f"Erro ao inserir/atualizar jogo '{game_id}': {e}", exc_info=True)
            raise
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir/atualizar jogo '{game_id}': {e}", exc_info=True)
            raise

    def insert_stats(self, stats_item):
        """Insere ou atualiza estatísticas de jogador para um jogo e quarto."""
        try:
            adapter = ItemAdapter(stats_item)
            player_id = adapter.get('player_id')
            game_id = adapter.get('game_id')
            team_id = adapter.get('team_id')
            quarter = adapter.get('quarter')

            if not all([player_id, game_id, team_id, quarter]):
                missing_fields = []
                if not player_id: missing_fields.append('player_id')
                if not game_id: missing_fields.append('game_id')
                if not team_id: missing_fields.append('team_id')
                if not quarter: missing_fields.append('quarter')
                
                logger.error(f"Dados essenciais faltando para player_stats (campos NULL: {', '.join(missing_fields)}). Item: {stats_item}")
                return 

            values_to_insert = (
                player_id, game_id, team_id, quarter,
                adapter.get('minutes_played'), adapter.get('assist'),
                adapter.get('points_attempts'), adapter.get('points_made'),
                adapter.get('defensive_rebounds'), adapter.get('offensive_rebounds'),
                adapter.get('three_points_attempts'), adapter.get('three_points_made'),
                adapter.get('two_points_attempts'), adapter.get('two_points_made'),
                adapter.get('free_throws_attempts'), adapter.get('free_throws_made'),
                adapter.get('steals'), adapter.get('blocks'),
                adapter.get('fouls_committed'), adapter.get('fouls_received'),
                adapter.get('total_errors'), adapter.get('dunks'),
                adapter.get('plus_minus_while_on_court'), adapter.get('efficiency')
            )
            
            self.cur.execute(
                """
                INSERT INTO player_stats (
                    player_id, game_id, team_id, quarter, minutes_played, assist,
                    points_attempts, points_made, defensive_rebounds, offensive_rebounds,
                    three_points_attempts, three_points_made, two_points_attempts, two_points_made,
                    free_throws_attempts, free_throws_made, steals, blocks,
                    fouls_committed, fouls_received, total_errors, dunks,
                    plus_minus_while_on_court, efficiency
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id, game_id, quarter) DO UPDATE
                SET minutes_played = EXCLUDED.minutes_played,
                    assist = EXCLUDED.assist,
                    points_attempts = EXCLUDED.points_attempts,
                    points_made = EXCLUDED.points_made,
                    defensive_rebounds = EXCLUDED.defensive_rebounds,
                    offensive_rebounds = EXCLUDED.offensive_rebounds,
                    three_points_attempts = EXCLUDED.three_points_attempts,
                    three_points_made = EXCLUDED.three_points_made,
                    two_points_attempts = EXCLUDED.two_points_attempts,
                    two_points_made = EXCLUDED.two_points_made,
                    free_throws_attempts = EXCLUDED.free_throws_attempts,
                    free_throws_made = EXCLUDED.free_throws_made,
                    steals = EXCLUDED.steals,
                    blocks = EXCLUDED.blocks,
                    fouls_committed = EXCLUDED.fouls_committed,
                    fouls_received = EXCLUDED.fouls_received,
                    total_errors = EXCLUDED.total_errors,
                    dunks = EXCLUDED.dunks,
                    plus_minus_while_on_court = EXCLUDED.plus_minus_while_on_court,
                    efficiency = EXCLUDED.efficiency,
                    team_id = EXCLUDED.team_id;
                """,
                values_to_insert
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback() 
            logger.error(f"Erro ao inserir/atualizar estatísticas para o jogador '{player_id}' no jogo '{game_id}', quarto '{quarter}': {e}", exc_info=True)
            raise 
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir/atualizar estatísticas para o jogador '{player_id}' no jogo '{game_id}', quarto '{quarter}': {e}", exc_info=True)
            raise

    def insert_shot(self, shot_item):
        """Insere um registro de arremesso."""
        try:
            adapter = ItemAdapter(shot_item)
            player_id = adapter.get('player_id')
            game_id = adapter.get('game_id')
            team_id = adapter.get('team_id') 

          
            if not all([player_id, game_id, team_id]): 
                logger.warning(f"Dados essenciais faltando para inserir arremesso (player_id, game_id ou team_id é NULL). Item: {shot_item}")
                return

            self.cur.execute(
                """
                INSERT INTO shots (
                    player_id, game_id, team_id, shot_quarter, shot_time,
                    shot_type, shot_x_location, shot_y_location
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s); 
                """,
                (
                    player_id, game_id, adapter.get('team_id'), adapter.get('shot_quarter'),
                    adapter.get('shot_time'), adapter.get('shot_type'),
                    adapter.get('shot_x_location'), adapter.get('shot_y_location')
                )
            )
        except (NotNullViolation, InFailedSqlTransaction, psycopg2.Error) as e:
            self.conn.rollback()
            logger.error(f"Erro ao inserir arremesso para o jogador '{player_id}' no jogo '{game_id}': {e}", exc_info=True)
            raise
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro inesperado ao inserir arremesso para o jogador '{player_id}' no jogo '{game_id}': {e}", exc_info=True)
            raise



if __name__ == "__main__":
    print("Tentando criar tabelas do banco de dados...")
    with DatabaseManager(DB_CONFIG) as db_manager_setup:
        db_manager_setup.create_tables()
    print("Configuração do banco de dados completa (se nenhum erro ocorreu). Verifique db_inserts.log para detalhes.")

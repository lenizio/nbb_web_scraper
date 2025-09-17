from nbb.items import GameItem, ShotItem, PlayerItem, TeamItem
from scrapy.exceptions import DropItem
from itemadapter import ItemAdapter
import hashlib
import logging
from nbb.db_manager import DatabaseManager, DB_CONFIG, close_pool
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class NbbPipeline:

    def __init__(self):
        pass

    def open_spider(self, spider):
        logger.info(f"Opening spider: {spider.name}. Pipeline pronto para processar itens.")
        try:
            with DatabaseManager(DB_CONFIG) as db:
                db.create_tables()  # ✅ Função que cria as tabelas
            logger.info("Tabelas verificadas/criadas com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao criar/verificar tabelas: {e}", exc_info=True)
            raise

    def close_spider(self, spider):    
        logger.info(f"Closing spider: {spider.name}. Pipeline finalizado.")
        try:
            close_pool()
        except Exception as e:
            logger.error(f"Erro ao fechar pool de conexões: {e}", exc_info=True)

    def generate_team_id(self, logo_url):        
        return hashlib.md5(logo_url.encode('utf-8')).hexdigest()

    def process_item(self, item, spider):
        """
        Processa cada item gerado pelo spider dentro de sua própria transação.
        """        
        try:
            with DatabaseManager(DB_CONFIG) as db:
                if isinstance(item, TeamItem):
                    self.process_team(db, item)
                elif isinstance(item, PlayerItem):
                    self.process_player(db, item)
                elif isinstance(item, GameItem):
                    db.insert_game(item)
                elif isinstance(item, ShotItem):
                    db.insert_shot(item)
                else:
                    logger.warning(f"Tipo de item desconhecido encontrado: {type(item)}")

            return item 
        
        except DropItem as e:
            logger.warning(f"Descartando item: {e} - Item: {item}")
            raise 
        except Exception as e:            
            logger.error(f"Erro ao processar item no pipeline: {e} - Item: {item}", exc_info=True)
            raise 

    def process_team(self, db, item):
        adapter = ItemAdapter(item)
        logo_url = adapter.get('logo')
        if not logo_url:
            raise DropItem("Item TeamItem sem URL de logo válido.")
        team_id = self.generate_team_id(logo_url)
        adapter['id'] = team_id
        db.insert_team(item)

    def process_player(self, db, item):
        adapter = ItemAdapter(item)
        player_id = adapter.get('player_id')
        if not player_id:
            raise DropItem("Item PlayerItem sem player_id válido.")
        db.insert_player(item)
        db.insert_player_team_by_season(item)

    def process_player_team_by_season(self, db, item):
        adapter = ItemAdapter(item)
        player_name = adapter.get('player_name')
        player_team_id = adapter.get('player_team_id')
        player_number = adapter.get('player_number')
        season = adapter.get('season')
        if not all([player_name, player_team_id, player_number, season]):
            raise DropItem(f"Item PlayerNumberItem incompleto: {item}")
        db.insert_player_team_by_season(item)

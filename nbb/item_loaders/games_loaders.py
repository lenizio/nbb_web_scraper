from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join  
from w3lib.html import remove_tags
from nbb.items import GameItem
import datetime 

def clean_string(text):
    return text.strip().replace('\n', '').replace('\r', '')

def parse_date(text):
    if text:
        try:
            return datetime.datetime.strptime(text, '%d/%m/%Y').date()
        except ValueError:
            return None
    return None

def parse_time(text):
    if text:
        try:
            text = text.replace('h', '')
            return datetime.datetime.strptime(text, '%H:%M').time()
        except ValueError:
            return None
    return None



class GameLoader(ItemLoader):
    
    default_item_class  = GameItem
    
    default_input_processor = MapCompose(clean_string)
    default_output_processor = TakeFirst()
    
    home_team_id_in = MapCompose(clean_string)
    away_team_id_in = MapCompose(clean_string)
    home_team_score_in = MapCompose(clean_string,int)
    away_team_score_in = MapCompose(clean_string,int)
    game_id_in = MapCompose(remove_tags,clean_string,int)
    game_date_in = MapCompose(clean_string, parse_date)
    game_time_in = MapCompose(clean_string, parse_time)
    date_out = Join()
    round_out = Join()
    
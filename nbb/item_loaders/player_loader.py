from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join  
from w3lib.html import remove_tags
from nbb.items import PlayerItem
import re

def clean_string(text):
    return text.strip().replace('\n', '').replace('\r', '')


class PlayerLoader(ItemLoader):
    default_item_class  = PlayerItem
    
    default_input_processor = MapCompose(clean_string)
    default_output_processor = TakeFirst()
    
    player_id_in = MapCompose(clean_string,int)
    player_team_id_in = MapCompose(clean_string)
    
    
    

    
      
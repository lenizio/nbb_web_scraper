from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join ,Identity 
from w3lib.html import remove_tags
from nbb.items import ShotItem
import re

def clean_string(text):
    return text.strip().replace('\n', '').replace('\r', '')

def extract_shot_x_location(text):
    match = re.search(r'top:\s*([\d.]+)%;\s*left:\s*([\d.]+)%', text)
    return float(match.group(2)) if match else 0.0

def extract_shot_y_location(text):
    match = re.search(r'top:\s*([\d.]+)%;\s*left:\s*([\d.]+)%', text)
    
    
    return float(match.group(1)) if match else 0.0


class ShotLoader(ItemLoader):
    default_item_class  = ShotItem
    
    default_input_processor = MapCompose(clean_string)
    default_output_processor = TakeFirst()
    
    shot_y_location_in =MapCompose(clean_string,extract_shot_y_location,float)
    shot_x_location_in =MapCompose(clean_string,extract_shot_x_location,float)
    
    game_id_in =Identity()
    
    player_id_in = MapCompose(clean_string,int)
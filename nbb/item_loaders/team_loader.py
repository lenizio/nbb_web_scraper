from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join ,Identity 
from w3lib.html import remove_tags
from nbb.items import TeamItem
import re


def clean_string(text):
    return text.strip().replace('\n', '').replace('\r', '')


class TeamLoader(ItemLoader):
    default_item_class  = TeamItem
    
    default_input_processor = MapCompose(clean_string)
    default_output_processor = TakeFirst()
    
    id_in = MapCompose(int)
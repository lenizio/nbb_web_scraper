import scrapy

class TeamItem(scrapy.Item):
    
    id = scrapy.Field()
    name = scrapy.Field()
    logo = scrapy.Field()

class GameItem(scrapy.Item):
    game_id = scrapy.Field()
    game_date = scrapy.Field()
    game_time = scrapy.Field()
    home_team_id = scrapy.Field()   
    away_team_id = scrapy.Field()
    home_team_score = scrapy.Field() 
    away_team_score = scrapy.Field()
    round = scrapy.Field()
    stage = scrapy.Field()
    season = scrapy.Field()
    arena = scrapy.Field()
    link = scrapy.Field()


class ShotItem(scrapy.Item):
    
    player_id = scrapy.Field()
    game_id = scrapy.Field()
    team_id = scrapy.Field()
    shot_quarter = scrapy.Field()
    shot_time = scrapy.Field()
    shot_type = scrapy.Field()
    shot_x_location = scrapy.Field()
    shot_y_location = scrapy.Field()
    
class PlayerItem(scrapy.Item):

    player_name = scrapy.Field()
    player_number = scrapy.Field()
    player_id = scrapy.Field()
    player_photo = scrapy.Field()
    player_team_id = scrapy.Field()
    season = scrapy.Field() 
    
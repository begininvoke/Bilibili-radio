import os

class Config:
    API_HOST = '0.0.0.0'
    API_PORT = 5000
    API_DEBUG = False
    
    BUFFER_MAX_SIZE = 1024 * 1024 * 10
    BUFFER_HIGH_WATERMARK = 0.8
    BUFFER_LOW_WATERMARK = 0.3
    
    PRODUCER_CHUNK_SIZE = 4096
    PRODUCER_MAX_RETRIES = 3
    PRODUCER_RETRY_DELAY = 2
    
    PLAYER_SAMPLE_RATE = 44100
    PLAYER_CHANNELS = 2
    PLAYER_CHUNK_SIZE = 4096
    
    MONITOR_INTERVAL = 3
    
    BILIBILI_API_TIMEOUT = 10
    
    @staticmethod
    def init_app():
        pass


class DevelopmentConfig(Config):
    API_DEBUG = True


class ProductionConfig(Config):
    API_DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

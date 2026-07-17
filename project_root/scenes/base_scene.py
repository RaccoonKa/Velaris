class BaseScene:
    def __init__(self, engine):
        self.engine = engine

    def on_enter(self, **kwargs):
        pass

    def handle_events(self, events):
        pass

    def update(self):
        pass

    def draw(self, window):
        pass

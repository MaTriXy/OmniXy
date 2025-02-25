class DriverFactory:
    def __init__(self):
        self.drivers = {}

    def register_driver(self, provider_name, driver_class):
        self.drivers[provider_name] = driver_class

    def create_driver(self, provider_name, provider_config):
        driver_class = self.drivers.get(provider_name)
        if not driver_class:
            raise ValueError(f"Driver {provider_name} not registered")
        return driver_class(provider_config)

from faker import Faker

# Initialize Faker with Indian locale as requested
fake = Faker('en_IN')

def set_seed(seed_value: int):
    """Set random seed for repeatability."""
    Faker.seed(seed_value)
    import random
    random.seed(seed_value)

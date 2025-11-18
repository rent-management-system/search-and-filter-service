from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base

# Define a common Base for all models
# This creates the Base class once.
Base = declarative_base(cls=AsyncAttrs)

# Import models AFTER Base is defined
# This ensures models inherit from the *same* Base instance
from . import property
from . import search
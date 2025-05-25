import warnings

# Suppress deprecation warning from passlib using crypt
warnings.filterwarnings("ignore", ".*crypt is deprecated.*", DeprecationWarning)

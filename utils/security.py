from passlib.context import CryptContext

pwd_content = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str):
    """
    获取密码的哈希值
    该函数接收一个明文密码字符串，使用pwd_content模块的hash函数对其进行哈希处理，
    返回处理后的哈希值。这是一种常见的密码安全存储方式，可以避免明文存储密码。
    参数:
        password (str): 需要进行哈希处理的明文密码
    返回:
        str: 密码的哈希值
    """
    return pwd_content.hash(password)  # 调用pwd_content模块的hash函数对密码进行哈希处理


def verify_password(password: str,hash_password: str):
    """
    验证密码
    该函数接收一个明文密码字符串和一个哈希密码字符串，使用pwd_content模块的verify函数对它们进行比较，
    返回比较结果。如果明文密码和哈希密码匹配，则返回True，否则返回False。
    参数:
        password (str): 需要验证的明文密码
        hash_password (str): 哈希密码
    返回:
        bool: 比较结果
    """
    return pwd_content.verify(password, hash_password)  # 调用pwd_content模块
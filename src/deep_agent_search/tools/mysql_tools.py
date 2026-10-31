import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from mysql.connector import connect

from deep_agent_search.api.monitor import monitor
from deep_agent_search.core.logger_utils import logger

load_dotenv(override=True)


def get_db_config():
    """生产用于连接数据库的配置函数"""

    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),  # 主机号
        "port": int(os.getenv("MYSQL_PORT", "3306")),  # 端口号
        "user": os.getenv("MYSQL_USER"),  # 用户名
        "password": os.getenv("MYSQL_PASSWORD"),  # 密码
        "database": os.getenv("MYSQL_DATABASE"),  # 数据库名
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),  # 字符集合
        "autoocommit": False,  # 自动提交事务
    }

    # 先过滤不合法的如None、""
    config = {key: value for key, value in config.items() if value}
    # 必须配置
    require_configs = ["user", "password", "database"]
    # 判断必配置的有没有配置
    missing_config = [
        req_config for req_config in require_configs if req_config not in config
    ]
    if missing_config:
        # 表示有没有配置的
        raise ValueError(f"缺少必填关键项:{','.join(missing_config)}")

    return config


_db_config = get_db_config()


@tool
def list_sql_tables() -> str:
    """
    列出所有可用的表

    Returns:
        str: 有表时：可用的表：a,b,c  没有表时：没有可用的表
    """

    logger.info("--------正在查询数据库中的表名--------")
    monitor.report_tool("list_sql_tables", {})
    try:
        # 连接数据库
        with connect(**_db_config) as conn:
            # 获取游标
            with conn.cursor() as cursor:
                # 执行sql
                cursor.execute("show tables;")
                # 通过游标获取结果
                result = cursor.fetchall()
                if not result:
                    return "没有可用的表"
                # result结构：[('drugs',), ('inventory',), ('sales_records',)]

                table_names_str = ",".join([item[0] for item in result])
                logger.info(f"可用的表：{table_names_str}")

                return f"可用的表：{table_names_str}"
    except Exception as e:
        raise f"连接数据库失败：{e!s}"


@tool
def get_table_data(table_name: str) -> str:
    """
    获取指定表名的前至多100条数据列表，同时带字段名列表

    Args:
        table_name (str): 表名

    Returns:
        str:
    表名：abc
    表数据
    id   name    age
    1  二狗子    18
    2  驴蛋蛋    19

    返回的结果数据： 查询结果有数据时："id,name,age\n1,二狗子,1\n2,驴蛋蛋,19"  查询结果没数据时：查询表abc,结果没有数据
    """

    logger.info(f"----正在查询表{table_name}的数据...")
    monitor.report_tool("get_table_data", {"table_name": table_name})
    try:
        # 连接数据库
        with connect(**_db_config) as conn:
            # 获取游标
            with conn.cursor() as cursor:
                # 查询表的前100个数据
                cursor.execute(f"select * from {table_name} limit 100")
                result = cursor.fetchall()
                if not result:
                    return f"查询表{table_name},结果没有数据"

                # 查询表中的所有字段信息，并拼接成字符串
                # id,name,age
                column_name_str = ",".join(cursor.column_names)
                # 1,二狗子,1\n2,驴蛋蛋,19"
                # map(str, row): 遍历row这个可迭代对象，将每个元素作为str()的参数，返回结果构成与新的可迭代对象(与原来可迭代对象类型一直)
                data_str = "\n".join([",".join(map(str, row)) for row in result])

                return column_name_str + "\n" + data_str
    except Exception as e:
        raise f"连接数据库失败：{e!s}"


@tool
def execute_sql_query(sql: str) -> str:
    """
    根据指定sql执行，返回查询的结果

    Args:
        sql (str): 由大模型生成的sql

    Returns:
        str: 字段列表和数据列表的字符串
    """
    logger.info(f"----正在执行SQL：{sql}")
    monitor.report_tool("execute_sql_query", {"sql": sql})
    try:
        # 连接数据库
        with connect(**_db_config) as conn:
            # 获取游标
            with conn.cursor() as cursor:
                # 执行sql
                cursor.execute(sql)
                # 获取sql对应表的所有字段，并拼接成字符串
                column_names_str = ",".join(cursor.column_names)
                # 获取sql的执行结果
                result = cursor.fetchall()
                if not result:
                    return f"执行{sql},结果没有数据"
                data_str = "\n".join([",".join(map(str, row)) for row in result])

                return column_names_str + "\n" + data_str

    except Exception as e:
        raise f"连接数据库失败：{e!s}"

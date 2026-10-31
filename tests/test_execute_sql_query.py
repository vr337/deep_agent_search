from deep_agent_search.tools.mysql_tools import execute_sql_query

if __name__=="__main__":
    print(execute_sql_query.invoke("select * from drugs limit 1"))
import os


def str_acesso(key='oracleProd'):
    ans = {}

    if key == 'oracleProd':
        ans = {'user': 'dbsm', 'password': 'wobistdu','host':'200.129.163.24', 'database': '','sid':'dbsie','port':1521}
    elif key == 'oracleDev':
        ans = {'user': 'dbsm', 'password': 'wobistdu','host':'10.206.200.207', 'database': '','sid':'dbsie','port':1521}

    return ans

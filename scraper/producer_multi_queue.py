from scraper.tasks_104_scraper import scrape_104_jobs_upload_mysql
from scraper.tasks_cake_scraper import scrape_cake_jobs_upload_mysql
from scraper.tasks_get_exchange_rate import refresh_exchange_rates
from loguru import logger

# ------ 104 ------ #
# start page and end page
start = 1
end = 35
search_terms = ['資料工程師', '資料分析師', '資料科學家', '軟體工程師', '大數據專員', 'python工程師']

for search_term in search_terms:
    for page_num in range(start, end+1):
        args = (search_term, page_num)
        task_104 = scrape_104_jobs_upload_mysql.s(*args)
        task_104.apply_async(queue='104_jobs') # send the task to the '104_jobs' queue
    print(f'{search_term} a total of:{end - start +1} tasks for 104 scraper sent to the queue!')



# # ------ Cake ------ #

# # the roles to look for on cake
search_keywords = ['data engineer', 'data analyst', 'ml engineer', 
                   'software engineer', 'software developer', 'database engineer']
start = 1
end = 35
for search_keyword in search_keywords:
    for page_num in range(start, end+1):
    # send the task to the 'cake_jobs' queue
        task_cake = scrape_cake_jobs_upload_mysql.s(search_keyword, page_num)
        task_cake.apply_async(queue='cake_jobs') # send the task to the 'cake_jobs' queue
        logger.info(f'{search_keyword} a total of:{end - start +1} tasks task for Cake scraper has been sent to the queue.')


# ------ fetch exchange rate ------ #
task_ex_rate = refresh_exchange_rates.s()
task_ex_rate.apply_async(queue='exchange') 
logger.info(f'Fetching exhcnage rate and uploading to database...')

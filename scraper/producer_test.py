from scraper.tasks_cake_scraper import scrape_cake_jobs_upload_mysql, scrape_cake_jobs
from scraper.tasks_104_scraper import scrape_104_jobs
from scraper.tasks_104_scraper import scrape_104_jobs_upload_mysql

# scrape_cake_jobs.delay('資料工程師')
# scrape_104_jobs.delay('資料工程師', 2)
# scrape_104_jobs_upload_mysql.delay()
scrape_104_jobs_upload_mysql.delay("軟體工程師", 1)

# search_term = 'data engineer'
# for num in range(1, 3):
#     args = ('data engineer', num)
#     print(f'=========loading page {num}...')
#     # scrape_cake_jobs(*args)
#     scrape_cake_jobs_upload_mysql.delay(*args)
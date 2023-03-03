import requests
from bs4 import BeautifulSoup

def extract_twitter_metadata(url, tagsSelector):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    tags_container = soup.select_one(tagsSelector)
    if tags_container is None:
        return []
    all_tags = tags_container.find_all('li')
    hash_tags = []
    for tag in all_tags:
       tag_link = tag.find('a')
       hash_tags.append("#"+tag_link.text.replace(" ", "").lower())

    keywords = []
    description = ''
    title = ''
    for meta in soup.find_all('meta'):
        if 'name' in meta.attrs and meta.attrs['name'] == 'keywords':
            keywords = meta.attrs['content'].split(',')
        if 'name' in meta.attrs and meta.attrs['name'] == 'twitter:description':
            description = meta.attrs['content']
        if 'name' in meta.attrs and meta.attrs['name'] == 'twitter:title':
            title = meta.attrs['content']
    return [keywords, hash_tags, title, description]

articles_cache = {}
def read_all_articles(domain, listContainerSelector, postSelector = 'article'):
    if domain in articles_cache:
        return articles_cache[domain]
    response = requests.get(domain)
    soup = BeautifulSoup(response.text, 'html.parser')

    all_posts = soup.select_one(listContainerSelector).find_all(postSelector)
    postLinks = []
    #  TODO: handle pagination
    for post in all_posts:
        postLinks.append(post.find('a').attrs['href'])
    articles_cache[domain] = postLinks
    return postLinks

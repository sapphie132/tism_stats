import math
import requests
import re

debug = False
page_limit = None

user_id = 290
forum_query = f"subject:*SFW*, user_id: {user_id}"

extra_query_term = "princest"
fave_query = f"faved_by_id: {user_id}, safe"
image_query = fave_query + ", " + extra_query_term
filter_id = 2 # Everything*

booru = "https://ponybooru.org"


def get_results(url_search, payload_key, page_limit):
    resp = requests.get(url_search)
    if debug:
        print(url_search)
        print(resp)
    resp = resp.json()
    
    if debug:
        print(resp.keys())
    results = resp[payload_key]
    total = resp["total"]
    if debug:
        print(len(results))
    print(f"Total: {total}")
    
    page = 2 # we just fetched page 1
    while len(results) < total:
        if page_limit is not None and page > page_limit:
            break
        print(f"Fetching page {page}")
        url_search_page = url_search + f"&page={page}"
        # TODO: add better handling of possible fucky-wuckery
        resp = requests.get(url_search_page)
        if debug:
            print(resp)
        resp = resp.json()
        page += 1
        new_res = resp[payload_key]
        if debug:
            print(len(new_res))
        results.extend(new_res)

    return results

def get_posts(page_limit = None):
    base_url_search = "/api/v1/json/search/posts"
    url_search = booru + base_url_search + f"?q={forum_query}&per_page=50"
    print("Fetching forum posts…")
    posts = get_results(url_search, "posts", page_limit)
    return posts

def get_images(page_limit = None):
    url_search = get_img_search_url(image_query)
    print("Fetching faved images…")
    images = get_results(url_search, "images", page_limit)
    return images

def get_total_faves():
    url_search = get_img_search_url(fave_query)
    if debug:
        print(fave_query)
        print(url_search)
    resp = requests.get(url_search)
    resp = resp.json()
    #print(resp)
    return resp['total']

def get_img_search_url(query):
    base_url_search = "/api/v1/json/search/images"
    url_search = booru + base_url_search + f"?q={query}&filter_id={filter_id}&per_page=50"
    return url_search

def mk_post_url(p_id):
    return f"https://ponybooru.org/forums/dis/topics/post-a-random-sfw-image-from-your-favorites?post_id={p_id}#post_{p_id}"

def calc_prob(n, p, i):
    total = 0
    for j in range(i+1):
        total += math.comb(n, j) * ((1-p) ** (n-j)) * (p ** j)

    return total


posts = get_posts(page_limit)
images = get_images(page_limit)

image_regex = re.compile(">>(\d+)")
post_images = {}
multiple_per_post = {}
for post in posts:
    body = post["body"]
    matches = image_regex.findall(body)
    p_id = post['id']
    if len(matches) > 1:
        multiple_per_post[p_id] = matches
    
    if len(matches) > 0:
        post_images[p_id] = int(matches[0])

# Haven't tested this, hopefully it works as intended and doesn't
# crash the program
if len(multiple_per_post.keys()) > 0:
    print("Warning: some posts containing multiple images were found.")
    print("Only the first image of each of those posts was taken into account")
    print("Offending posts:")
    for p_id in multiple_per_post:
        imgs = multiple_per_post[p_id]
        print(mk_post_url(p_id) + f" ({', '.join(imgs)})")

# Converting to set for quicker lookup
fave_images = set([image['id'] for image in images])
total_faves = get_total_faves()
overlap = 0

# Using a set for post_images wouldn't work
# because an image can occasionally be picked twice
# for the thread
print("\n====================================\n")
print("Posts containing the queried images:")
for p_id in post_images:
    img = post_images[p_id]
    if img in fave_images:
        overlap += 1
        print(mk_post_url(p_id))

p = len(fave_images) / total_faves 
expected_value = p * len(post_images)

print(f"Images in your (safe) favourites matching the query: {len(fave_images)}")
print(f"Total (safe) images in your faves: {total_faves}")
print(f"Posts (that contain at least one image) made in the thread: {len(post_images)}")
print(f"Images from this query that were posted to the thread: {overlap}")
print(f"Expected value: {expected_value}")
p_more_eq = calc_prob(len(post_images), p, overlap)
print(f"Probability of randomising {overlap} or more images from this query: {p_more_eq}")
print(f"Probability of randomising less than {overlap} images from this query: {1-p_more_eq}")

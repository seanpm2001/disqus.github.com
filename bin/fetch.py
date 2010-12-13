from feedreader.parser import from_url
import cgi
import codecs
import datetime
import logging
import os.path
import re
import sqlite3

try:
    from settings import *
except ImportError:
    pass

conn = sqlite3.connect('db.sqlite')
conn.isolation_level = None

FEEDS = (
    # ('DISQUS USERNAME', 'DISQUS FORUM SHORTNAME', 'FEED URL'),
    ('zeeg', 'davidcramer', 'http://www.davidcramer.net/disqus/feed'),
    ('dz', 'nodnod', 'http://blog.nodnod.net/tagged/disqus/rss'),
    ('disqus', 'disqus', 'http://blog.disqus.com/tagged/dev/rss'),
    ('bretthoerner', 'bretthoerner', 'http://bretthoerner.com/tags/disqus/feed.atom'),
    ('antonkovalyov', 'self', 'http://anton.kovalyov.net/disqus.xml'),
)

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    value = re.sub('[-\s]+', '-', value)
    return value

def linebreaks(value, autoescape=False):
    """Converts newlines into <p> and <br />s."""
    value = re.sub(r'\r\n|\r|\n', '\n', unicode(value)) # normalize newlines
    paras = re.split('\n{2,}', value)
    if autoescape:
        paras = [u'<p>%s</p>' % cgi.escape(p).replace('\n', '<br />') for p in paras]
    else:
        paras = [u'<p>%s</p>' % p.replace('\n', '<br />') for p in paras]
    return u'\n\n'.join(paras)

class FeedAggregator(object):
    def collect(self, author, forum, feed_url):
        feed = from_url(feed_url)
        for entry in feed.entries:
            cursor = conn.cursor()
            cursor.execute('select 1 from entries where url = ? limit 1', [unicode(entry.link)])
            if not cursor.fetchall():
                slug = '%s-%s' % (author, slugify(unicode(entry.title)))
                self.write(author, forum, entry.link, entry.title,
                           entry.description, entry.published, slug)
                cursor.execute('insert into entries values(?)', [unicode(entry.link)])
    
    def write(self, disqus_username, disqus_forum, url, title, body, date=None, slug=None):
        if not url:
            return
        
        print "Saving", url

        if not date:
            date = datetime.datetime.now()
        
        filename = date.strftime('%Y-%m-%d-%%s.html') % slug
        
        outfile = codecs.open(os.path.join(os.path.dirname(__file__), '..', '_posts', filename), 'wb', 'utf-8')
        
        template = open(os.path.join(os.path.dirname(__file__), '..', '_templates', 'post.html'), 'r').read()
        
        if not body.startswith('<'):
            body = linebreaks(body)
            
        body = body.replace('{', '&#123;')\
                   .replace('}', '&#125;')
        
        data = {
            'disqus_forum': disqus_forum,
            'title': title,
            'url': url,
            'slug': slug,
            'body': body,
            'disqus_username': disqus_username,
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        outfile.write(template % data)
        outfile.close()

def main():
    conn.execute('create table if not exists entries (url text)')
    
    agg = FeedAggregator()
    for author, forum, feed in FEEDS:
        try:
            agg.collect(author, forum, feed)
        except Exception, e:
            logging.exception(e)

if __name__ == '__main__':
    main()
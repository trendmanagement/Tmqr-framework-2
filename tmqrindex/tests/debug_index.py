from tmqrfeed.manager import DataManager
from tmqrindex.index_contfut import IndexContFut

if __name__ == '__main__':
    dm = DataManager()
    index = IndexContFut(dm, instrument='US.ES')
    index.run()

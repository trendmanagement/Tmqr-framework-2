from tmqrfeed.contracts import FutureContract


class FutureChain:
    """
    Futures chain class
    """

    def __init__(self, fut_tckr_list):
        self.futures = [FutureContract(f) for f in fut_tckr_list]

    def __len__(self):
        return len(self.futures)

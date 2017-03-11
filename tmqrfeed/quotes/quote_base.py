class QuoteBase:
    """
    Quotes making base class. Creates different kinds of quotes based on processing raw quotes.
    """

    def do_futref_checks(self):
        """
        Do extra sanity checks to make sure that old quotes are not changing when new data arrives, could be useful
        for some smart quotes algorithms.
        :return:
        """
        pass

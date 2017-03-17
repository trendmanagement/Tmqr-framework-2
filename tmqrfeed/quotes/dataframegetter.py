class DataFrameGetter:
    """
    Implementation of quick Pandas.DataFrame get by label
    Because:
    dataframe['label'].value has overhead due to row-like data alignment inside dataframe
    """

    def __init__(self, df):
        """
        Initiation of fast DF getter
        :param df: Pandas.DataFrame
        """
        # Transpose dataframe data to make it column oriented
        self.data = df.values.T
        self.index = df.index

        self.cols = {}
        for i, col_name in enumerate(df.columns):
            self.cols[col_name] = i

    def __getitem__(self, col_name):
        """
        Returns pandas series by label
        :param col_name: column name
        :return: np.ndarray as stored in dataframe[col_name].values
        """
        return self.data[self.cols[col_name]]

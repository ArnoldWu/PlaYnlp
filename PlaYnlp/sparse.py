# -*- coding: utf-8 -*-

import numpy as np
from scipy import sparse
import pandas as pd
from .dataio import write_pickle_file

# L1_norm_col_summarizer = lambda xx:np.abs(xx).sum(axis=0)
# L0_norm_col_summarizer = lambda xx:xx.sign().sum(axis=0)

def L1_norm_col_summarizer(xx):
    return np.abs(xx).sum(axis=0)

def L0_norm_col_summarizer(xx):
    return xx.sign().sum(axis=0)


def gen_ptrs_idx(idx, idx_dtype=None):
    if idx_dtype == None:
        dt = np.dtype([("ptr", np.int64), ("idx", idx.dtype)])
    else:
        dt = np.dtype([("ptr", np.int64), ("idx", idx_dtype)])
    ptrs_idx = np.array(zip(np.arange(len(idx), dtype=np.int64), idx), dtype=dt)
    return ptrs_idx

def ptrs_idx_projection(ptrs_idx, proj_idx):
    return ptrs_idx[np.in1d(ptrs_idx["idx"], proj_idx)]

def sort_by_idx(ptrs_idx):
    return np.sort(ptrs_idx, order=["idx"])



class SparseDataFrameSummary(dict):
    _key_mapper = {"data":"summary_data",
                   "idx":"summary_idx", }

    def __init__(self, summary_data, summary_idx, sdf=None, **kwargs):
        self["summary_data"] = summary_data
        self["summary_idx"] = summary_idx

        if sdf != None:
            self["sdf"] = sdf
            if self["sdf"].is_matched_col_shape(self['summary_data']):
                self["summary_type"] = "col"

            if self["sdf"].is_matched_row_shape(self['summary_data']):
                self["summary_type"] = "row"

        self.update(kwargs)


    def __getstate__(self):
        pass


    def __setstate__(self, state):
        pass


    def __getattr__(self, key):

        if key.startswith("_") and key[1:] in self.keys():
            return self[key[1:]]
        else:

            if key.startswith("_") and key[1:] in self._key_mapper.keys() and self._key_mapper[key[1:]] in self.keys():
                return self[self._key_mapper[key[1:]]]
            else:
                return None


    def __lt__(self, upper_bound):
        return type(self)(summary_data=self["summary_data"] < upper_bound,
                          summary_idx=self["summary_idx"],
                          sdf=self["sdf"])


    def __le__(self, upper_bound):
        return type(self)(summary_data=self["summary_data"] <= upper_bound,
                          summary_idx=self["summary_idx"],
                          sdf=self["sdf"])


    def __gt__(self, lower_bound):
        return type(self)(summary_data=self["summary_data"] > lower_bound,
                          summary_idx=self["summary_idx"],
                          sdf=self["sdf"])


    def __ge__(self, lower_bound):
        return type(self)(summary_data=self["summary_data"] > lower_bound,
                              summary_idx=self["summary_idx"],
                              sdf=self["sdf"])


    def __and__(self, other_summary):
        assert isinstance(other_summary, type(self))
        assert np.array_equal(self["summary_idx"], other_summary["summary_idx"])
        assert self['summary_data'].dtype == np.bool
        assert other_summary['summary_data'].dtype == np.bool

        return type(self)(summary_data=self["summary_data"] & other_summary['summary_data'],
                          summary_idx=self["summary_idx"],
                          sdf=self["sdf"])

    @property
    def _is_bool(self):
        return self['summary_data'].dtype == np.bool

#    @property
#    def _is_sortable(self):
#        return isinstance(self['summary_data'].dtype, (np.int, np.float))

    @property
    def _has_sdf(self):
        return "sdf" in self.keys()

    @property
    def _filtered_idx(self):
        assert self._is_bool

        return self["summary_idx"][self['summary_data']]

    @property
    def _filtered_ptrs(self):
        assert self._is_bool

        _ptr = np.nonzero(self['summary_data'])

        if len(_ptr) == 1:
            _ptr = _ptr[0]

        return _ptr

    @property
    def _summary_type(self):
        assert self._has_sdf
        return self["summary_type"]


    @property
    def _sub_sdf(self):
        assert self._is_bool and self._has_sdf

        if self["sdf"].is_matched_col_shape(self['summary_data']):
            return self["sdf"].select_columns(select_col=self['summary_data'])

        if self["sdf"].is_matched_row_shape(self['summary_data']):
            return self["sdf"].select_rows(select_row=self['summary_data'])

    @property
    def _argsort_ptrs(self):
#        assert self._is_sortable
        return self._data.argsort()

    def top_k_ptrs(self, k=20, reverse=False):
        if reverse:
            return self._argsort_ptrs[:k]
        else:
            return self._argsort_ptrs[-k:]

    def top_k_idx(self, k=20, reverse=False):
        return self._idx[self.top_k_ptrs(k, reverse)]


class SparseDataFrame(dict):
    _key_mapper = {}
    _summerizer_class = SparseDataFrameSummary
    _dump_file_prefix = "sdf"

    def __init__(self, smatrix, col_idx=None, row_idx=None, summarizer=None):
        self["smatrix"] = smatrix

        if col_idx != None:
            assert isinstance(col_idx, (list, np.ndarray))

            if isinstance(col_idx, list):
                assert self["smatrix"].shape[1] == len(col_idx)
                self["col_idx"] = np.array(col_idx)

            else:
                assert self["smatrix"].shape[1] == col_idx.shape[0]
                self["col_idx"] = np.array(col_idx)
        else:
            self["col_idx"] = np.arange(self["smatrix"].shape[1])


        if row_idx != None:
            assert isinstance(row_idx, (list, np.ndarray))

            if isinstance(row_idx, list):
                assert self["smatrix"].shape[0] == len(row_idx)
                self["row_idx"] = np.array(row_idx)

            else:
                assert self["smatrix"].shape[0] == row_idx.shape[0]
                self["row_idx"] = np.array(row_idx)

        else:
            self["row_idx"] = np.arange(self["smatrix"].shape[0])


        if summarizer != None and callable(summarizer):
            self["summarizer"] = summarizer


    def __getstate__(self):
        pass


    def __setstate__(self, state):
        pass


    def __getattr__(self, key):

        if key.startswith("_") and key[1:] in self.keys():
            return self[key[1:]]
        else:

            if key.startswith("_") and key[1:] in self._key_mapper.keys() and self._key_mapper[key[1:]] in self.keys():
                return self[self._key_mapper[key[1:]]]
            else:
                return None


#     @property
#     def _smatrix(self):
#         return self["smatrix"]

#     @property
#     def _col_idx(self):
#         return self["col_idx"]

#     @property
#     def _row_idx(self):
#         return self["row_idx"]


    @property
    def T(self):
        tr_sdf = type(self)(smatrix=self["smatrix"].T,
                            col_idx=self["row_idx"],
                            row_idx=self["col_idx"],
                            summarizer=self["summarizer"] if self._has_default_summarizer else None)
        return tr_sdf


    @property
    def _has_default_summarizer(self):
        return "summarizer" in self.keys()


    @property
    def summary(self):
        if self._has_default_summarizer:
            return self.summarize_sdf(summarizer=self["summarizer"])


    def change_default_summerizer(self, summarizer=None):
        if summarizer != None and callable(summarizer):
            self["summarizer"] = summarizer
            return True
        else:
            return False


    def summarize_sdf(self, summarizer=L1_norm_col_summarizer):

        summary_data = summarizer(self["smatrix"])

        if len(summary_data.shape) == 1:
            _summary_data = summary_data
        else:
            assert len(summary_data.shape) == 2
            assert summary_data.shape[0] == 1 or summary_data.shape[1] == 1

            if summary_data.shape[0] == 1:
                _summary_data = np.array(summary_data)[0, :]
            else:
                _summary_data = np.array(summary_data)[:, 0]


        if _summary_data.shape[0] == self["smatrix"].shape[0]:
            return self._summerizer_class(summary_data=_summary_data,
                                          summary_idx=self["row_idx"],
                                          sdf=self)

        if _summary_data.shape[0] == self["smatrix"].shape[1]:
            return self._summerizer_class(summary_data=_summary_data,
                                          summary_idx=self["col_idx"],
                                          sdf=self)


    def select_columns(self, select_col=None):

        if select_col != None:
            if isinstance(select_col, self._summerizer_class) and select_col._is_bool:
                _select_col_idx = select_col._data
            else:
                _select_col_idx = select_col
        else:
            _select_col_idx = np.arange(len(self["col_idx"]))

        new_col_idx = self["col_idx"][_select_col_idx]

        new_smatrix = self["smatrix"][:, _select_col_idx]

        return type(self)(smatrix=new_smatrix,
                          col_idx=new_col_idx,
                          row_idx=self["row_idx"],
                          summarizer=self["summarizer"] if self._has_default_summarizer else None)


    def select_rows(self, select_row=None):
        if select_row != None:
            if isinstance(select_row, self._summerizer_class) and select_row._is_bool:
                _select_row_idx = select_row._data
            else:
                _select_row_idx = select_row
        else:
            _select_row_idx = np.arange(len(self["row_idx"]))

        new_row_idx = self["row_idx"][_select_row_idx]

        new_smatrix = self["smatrix"][_select_row_idx, :]

        return type(self)(smatrix=new_smatrix,
                          col_idx=self["col_idx"],
                          row_idx=new_row_idx,
                          summarizer=self["summarizer"] if self._has_default_summarizer else None)


    def sub_sdf(self, select_col=None, select_row=None):
        return self.select_columns(select_col).select_rows(select_row)


    def is_matched_col_shape(self, vec):
        if isinstance(vec, list):
            return len(vec) == self["smatrix"].shape[1]

        if isinstance(vec, np.ndarray):
            assert len(vec.shape) == 1
            return vec.shape[0] == self["smatrix"].shape[1]

    def is_matched_row_shape(self, vec):
        if isinstance(vec, list):
            return len(vec) == self["smatrix"].shape[0]

        if isinstance(vec, np.ndarray):
            assert len(vec.shape) == 1
            return vec.shape[0] == self["smatrix"].shape[0]


    def is_col_vec(self, vec):
        return self.is_matched_row_shape(vec)


    def is_row_vec(self, vec):
        return self.is_matched_col_shape(vec)


    def to_pickle_file(self, output_file, with_prefix=True, close_after_dump=True):

        return write_pickle_file(obj=self,
                                 write_file=output_file,
                                 write_file_prefix=with_prefix,
                                 close_after_write=close_after_dump)

#        if isinstance(output_file, file):
#            assert not output_file.closed
#            pickle.dump(self, output_file)
#
#            if close_after_dump:
#                output_file.close()
#
#
#        elif isinstance(output_file, (str,unicode)):
#            #TODO: output_file includes filename and path
#            with open(output_file, "wb") as wfile:
#                pickle.dump(self, wfile)


    def find_col_ptrs(self, finding_idx):

        # check finding_idx is subset of self._col_idx
        assert len(np.setdiff1d(finding_idx, self._col_idx)) == 0

        return np.r_[map(lambda xx:np.nonzero(self._col_idx == xx)[0], finding_idx)].T[0]

    def find_row_ptrs(self, finding_idx):

        # check finding_idx is subset of self._row_idx
        assert len(np.setdiff1d(finding_idx, self._row_idx)) == 0

        return np.r_[map(lambda xx:np.nonzero(self._row_idx == xx)[0], finding_idx)].T[0]


    def extend_zeros_cols(self, sdf):

        # TODO: this method could be rewritten with kronecker product (try it and test the speed ...)s

        sdf_diff_self_col_idx = np.setdiff1d(sdf._col_idx, self._col_idx)

        # subset checking:
        if len(sdf_diff_self_col_idx) > 0:

            # if it is not subset, extending self._col_idx

            ext_zeros_cols = type(self._smatrix)((self._smatrix.shape[0], len(sdf_diff_self_col_idx)),
                                                 dtype=self._smatrix.dtype)

            extended_smatrix = sparse.hstack([self._smatrix, ext_zeros_cols]).tocsc()

            extended_col_idx = np.r_[self._col_idx, sdf_diff_self_col_idx]


            return type(self)(smatrix=extended_smatrix,
                              col_idx=extended_col_idx,
                              row_idx=self["row_idx"],
                              summarizer=self["summarizer"] if self._has_default_summarizer else None)


        else:
            # if it is subset, do nothing
            return self


    def merge_sdf(self, sdf, method="replace"):
        """
        method in ("force_append","keep","replace","sum","mean")
        
        method == "force_append" means it will append all rows in sdf as new rows in self
        method == "keep" means if self and sdf have same idx rows, it will keep the rows from self
        method == "replace" means if self and sdf have same idx rows, it will replace with sdf's rows
        method == "sum" means if self and sdf have same idx rows, it will replace the rows as sum of sdf and self
        method == "mean" means if self and sdf have same idx rows, it will replace the rows as mean of sdf and self
        """

        assert method in ("force_append", "keep", "replace", "sum", "mean")


        self_ext_cols = self.extend_zeros_cols(sdf)
        sdf_ext_cols = sdf.extend_zeros_cols(self)

        _union_idx = np.r_[self_ext_cols._col_idx, sdf_ext_cols._col_idx]
        self_col_ptrs_idx = gen_ptrs_idx(self_ext_cols._col_idx, _union_idx.dtype)
        sdf_col_ptrs_idx = gen_ptrs_idx(sdf_ext_cols._col_idx, _union_idx.dtype)

        _union_idx = np.r_[self_ext_cols._row_idx, sdf_ext_cols._row_idx]
        self_row_ptrs_idx = gen_ptrs_idx(self_ext_cols._row_idx, _union_idx.dtype)
        sdf_row_ptrs_idx = gen_ptrs_idx(sdf_ext_cols._row_idx, _union_idx.dtype)


        inter_col_idx = np.intersect1d(self_col_ptrs_idx["idx"], sdf_col_ptrs_idx["idx"])
        inter_row_idx = np.intersect1d(self_row_ptrs_idx["idx"], sdf_row_ptrs_idx["idx"])


        self_inter_col_ptrs_idx = sort_by_idx(ptrs_idx_projection(self_col_ptrs_idx, inter_col_idx))
        sdf_inter_col_ptrs_idx = sort_by_idx(ptrs_idx_projection(sdf_col_ptrs_idx, inter_col_idx))

        self_inter_row_ptrs_idx = sort_by_idx(ptrs_idx_projection(self_row_ptrs_idx, inter_row_idx))
        sdf_inter_row_ptrs_idx = sort_by_idx(ptrs_idx_projection(sdf_row_ptrs_idx, inter_row_idx))


        self_only_row_ptrs_idx = np.setdiff1d(self_row_ptrs_idx, self_inter_row_ptrs_idx)
        sdf_only_row_ptrs_idx = np.setdiff1d(sdf_row_ptrs_idx, sdf_inter_row_ptrs_idx)


        self_ext_cols_smatrix = self_ext_cols._smatrix[:, self_inter_col_ptrs_idx["ptr"]]
        sdf_ext_cols_smatrix = sdf_ext_cols._smatrix[:, sdf_inter_col_ptrs_idx["ptr"]]

        if method in ("keep", "replace", "sum", "mean"):
            if method == "keep":
#                print 'self_only_row_ptrs_idx["idx"] = ',self_only_row_ptrs_idx["idx"]
#                print 'self_inter_row_ptrs_idx["idx"] = ',self_inter_row_ptrs_idx["idx"]
#                print 'sdf_only_row_ptrs_idx["idx"] = ',sdf_only_row_ptrs_idx["idx"]

                vstack_smatrix = [self_ext_cols_smatrix[self_only_row_ptrs_idx["ptr"], :]]
                new_row_idx = self_only_row_ptrs_idx["idx"]


                if self_inter_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(self_ext_cols_smatrix[self_inter_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        self_inter_row_ptrs_idx["idx"]]


                if sdf_only_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_only_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_only_row_ptrs_idx["idx"]]


                new_smatrix = sparse.vstack(vstack_smatrix).tocsc()
                new_col_idx = self_inter_col_ptrs_idx["idx"]


            elif method == "replace":

                vstack_smatrix = [self_ext_cols_smatrix[self_only_row_ptrs_idx["ptr"], :]]
                new_row_idx = self_only_row_ptrs_idx["idx"]


                if sdf_inter_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_inter_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_inter_row_ptrs_idx["idx"]]


                if sdf_only_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_only_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_only_row_ptrs_idx["idx"]]


                new_smatrix = sparse.vstack(vstack_smatrix).tocsc()
                new_col_idx = self_inter_col_ptrs_idx["idx"]



            elif method == "sum":

                vstack_smatrix = [self_ext_cols_smatrix[self_only_row_ptrs_idx["ptr"], :]]
                new_row_idx = self_only_row_ptrs_idx["idx"]


                if sdf_inter_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_inter_row_ptrs_idx["ptr"], :] + self_ext_cols_smatrix[self_inter_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_inter_row_ptrs_idx["idx"]]


                if sdf_only_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_only_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_only_row_ptrs_idx["idx"]]


                new_smatrix = sparse.vstack(vstack_smatrix).tocsc()
                new_col_idx = self_inter_col_ptrs_idx["idx"]



            elif method == "mean":

                vstack_smatrix = [self_ext_cols_smatrix[self_only_row_ptrs_idx["ptr"], :]]
                new_row_idx = self_only_row_ptrs_idx["idx"]


                if sdf_inter_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append((sdf_ext_cols_smatrix[sdf_inter_row_ptrs_idx["ptr"], :] + self_ext_cols_smatrix[self_inter_row_ptrs_idx["ptr"], :]) / 2.0)

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_inter_row_ptrs_idx["idx"]]


                if sdf_only_row_ptrs_idx["ptr"].size > 0:

                    vstack_smatrix.append(sdf_ext_cols_smatrix[sdf_only_row_ptrs_idx["ptr"], :])

                    new_row_idx = np.r_[new_row_idx,
                                        sdf_only_row_ptrs_idx["idx"]]


                new_smatrix = sparse.vstack(vstack_smatrix).tocsc()
                new_col_idx = self_inter_col_ptrs_idx["idx"]


        elif method == "force_append":

            new_smatrix = sparse.vstack([self_ext_cols_smatrix,
                                         sdf_ext_cols_smatrix]).tocsc()

            new_col_idx = self_inter_col_ptrs_idx["idx"]
            new_row_idx = np.r_[self_ext_cols._row_idx,
                                sdf_ext_cols._row_idx]



        return type(self)(smatrix=new_smatrix,
                          col_idx=new_col_idx,
                          row_idx=new_row_idx,
                          summarizer=self["summarizer"] if self._has_default_summarizer else None)


    @property
    def to_pandas_df(self):
        # TODO: write a general converting output class Convert and interfaces
        # sdf.to = Convert(self, ...)
        # sdf.to.pandas = Convert(sdf, ...).pandas ...

        return pd.DataFrame(self._smatrix.todense(), columns=self._col_idx, index=self._row_idx)


















if __name__ == '__main__':
    pass

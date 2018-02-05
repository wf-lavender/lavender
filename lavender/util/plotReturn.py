"""

"""
from pylab import *
import numpy as np
import re

rc_dict = {}


def plot_xy(x, y, save_path=None, **kwargs):
    """
    Deprecated!
    """
    matplotlib.style.use("bmh")
    fig = figure()
    ax = fig.add_subplot(111)

    fsize = 18
    if 'fsize' in kwargs:
        fsize = kwargs['fsize']

    if 'title' in kwargs:
        ax.set_title(kwargs['title'], fontsize=fsize)

    if 'xtitle' in kwargs:
        xtitle = kwargs['xtitle']
        ax.set_xlabel(xtitle, fontsize=fsize)

    if 'ytitle' in kwargs:
        ytitle = kwargs['ytitle']
        ax.set_ylabel(ytitle, fontsize=fsize)

    if 'n_xticks' in kwargs:
        n_xticks = kwargs['n_xticks']
        ax.set_xticks(np.linspace(x[0], x[-1], n_xticks))

    line_style = 'r-'
    if 'style' in kwargs:
        line_style = kwargs['style']

    if 'log' in kwargs:
        if kwargs['log']:
            ax.set_yscale('log')

    ax.plot(x, y, line_style)
    if save_path is not None:
        savefig(save_path)
    else:
        show()


class GenPlot:
    """
    class to generate plots of k line and other indicators.
    """
    def __init__(self, k_line):
        self.k_line = k_line

    def series_line(self, *variables, **kwargs):
        """
        Args:
            *variables:
            **kwargs:

        Returns:
        """
        matplotlib.style.use("bmh")
        figure()
        rcParams['font.sans-serif'] = ['FangSong']
        if 'title' in kwargs:
            title(kwargs['title'].decode('utf8'))

        std_up = None
        std_down = None
        variables = list(variables)
        for ikey in variables:
            if ikey not in self.k_line:
                print "warning: %s not in %s" % (ikey, str(self.k_line.columns.values))
                variables.remove(ikey)
            else:
                if "STD" in ikey:
                    std_days = re.search('\d+', ikey).group()
                    if "MA"+std_days in self.k_line:
                        ma_series = self.k_line["MA"+std_days]
                        std_series = self.k_line[ikey]
                        std_up = ma_series + std_series
                        std_up.name = "STD"
                        std_down = ma_series - std_series
                    else:
                        print "warning: %s-relative MA line not exist in %s" \
                                    % (ikey, str(self.k_line.columns.values))
                    variables.remove(ikey)
        series_list = [self.k_line[ikey] for ikey in variables]
        if std_up is not None and std_down is not None:
            plot(self.k_line.index, std_up, 'k--')
            plot(self.k_line.index, std_down, 'k--')

        for i_series in series_list:
            plot_date(self.k_line.index, i_series, '-')
        legend(loc="upper left", framealpha=0.5)
        show()
        savefig('series_line.png')

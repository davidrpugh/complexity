# import threading

import numpy as np

from chaco.api import ArrayPlotData, Plot
from enable.api import ComponentEditor
from encore.events.api import EventManager, HeartbeatEvent, Heartbeat
from traits.api import (HasTraits, Array, Bool, Button, DelegatesTo,  # Float,
                        Instance, Int, Property, Range, String)
from traitsui.api import ButtonEditor, Item, RangeEditor, View

history_length = 500


class Forest(HasTraits):
    p_lightning = Range(0., 1., 0.01)
    p_sapling = Range(0., 1., 0.02)
    forest_grid = Array(dtype=bool)
    forest_fires = Array(dtype=bool)
    size_x = Int(100)
    size_y = Int(100)

    def _forest_trees_default(self):
        return np.zeros((self.size_x, self.size_y))

    def _forest_fires_default(self):
        return np.zeros((self.size_x, self.size_y))

    def advance_one_day(self):
        self.grow_trees()
        self.burn_trees()
        self.start_fires()

    def grow_trees(self):
        growth_sites = np.random.uniform(size=(self.size_x, self.size_y)) <= \
            self.p_sapling
        self.forest_trees[growth_sites] = True

    def burn_trees(self):
        neighbor_on_fire = np.zeros((self.size_x, self.size_y), dtype=bool)
        north = self.forest_fires[:-2, 1:-1]
        south = self.forest_fires[2:, 1:-1]
        east = self.forest_fires[1:-1, :-2]
        west = self.forest_fires[1:-1, 2:]
        neighbor_on_fire[1:-1, 1:-1] = np.logical_or(
            north, np.logical_or(south, np.logical_or(east, west)))
        # print "{} squares with neighbors on fire".format(
        #     np.sum(neighbor_on_fire))
        new_fires = np.logical_and(neighbor_on_fire, self.forest_grid)
        # print "{} new fires by spreading".format(np.sum(new_fires))
        self.forest_grid[self.forest_fires] = False
        # print "{} trees burned down".format(np.sum(self.forest_fires))
        self.forest_fires = new_fires

    def start_fires(self):
        fire_sites = np.logical_and(np.random.uniform(
            size=(self.size_x, self.size_y)) <= self.p_lightning,
        # print "{} new fire sites".format(np.sum(fire_sites))
        self.forest_fires[fire_sites] = True
            self.forest_trees)


class ForestView(HasTraits):
    em = Instance(EventManager)
    hb = Instance(Heartbeat)
    forest = Instance(Forest)
    day = Button("Advance 1 Day")
    p_sapling = DelegatesTo("forest", "p_sapling")
    p_lightning = DelegatesTo("forest", "p_lightning")
    forest_plot = Instance(Plot)
    time_plot = Instance(Plot)
    ratio_history = Array(dtype=float)
    fire_history = Array(dtype=float)
    time = Array(dtype=int)
    plot_data = Instance(ArrayPlotData)
    run_label = Property(String, depends_on="run")
    run_button = Button
    run = Bool

    traits_view = View(
        Item("forest_plot", editor=ComponentEditor(), show_label=False),
        Item("time_plot", editor=ComponentEditor(), show_label=False),
        Item("p_sapling", editor=RangeEditor(), label="p sapling"),
        Item("p_lightning", editor=RangeEditor(), label="p lightning"),
        Item("run_button", editor=ButtonEditor(label_value="run_label"),
             show_label=False),
        Item("day", show_label=False),
        resizable=True,
    )

    def hb_listener(self, event):
        self._advance()
        event.mark_as_handled()

    def update_fire_history(self):
        self.fire_history[1:] = self.fire_history[:-1]
        self.fire_history[0] = float(np.sum(self.forest.forest_fires)) / \
            self.forest.forest_fires.size

    def update_ratio_history(self):
        self.ratio_history[1:] = self.ratio_history[:-1]
        self.tree_history[0] = float(np.sum(self.forest.forest_trees)) / \
            self.forest.forest_trees.size

    def update_time(self):
        self.time[1:] = self.time[:-1]
        self.time[0] = self.time[1] + 1

    def _advance(self):
        self.forest.advance_one_day()
        self.update_fire_history()
        self.update_ratio_history()
        self.update_time()
        self.plot_data.set_data("forest_grid", self.forest.forest_grid +
                                2 * self.forest.forest_fires)
        self.plot_data.set_data("fire_history", self.fire_history)
        self.plot_data.set_data("ratio_history", self.ratio_history)
        self.plot_data.set_data("time", self.time)

    def _day_fired(self):
        self._advance()

    def _em_default(self):
        em = EventManager()
        return em

    def _fire_history_default(self):
        return np.zeros((history_length, ), dtype=float)

    def _get_run_label(self):
        if self.run:
            label = "Stop"
        else:
            label = "Run"
        return label

    def _hb_default(self):
        return Heartbeat(interval=0.05, event_manager=self.em)

    def _ratio_history_default(self):
        return np.zeros((history_length, ), dtype=float)

    def _run_button_fired(self):
        if self.run:
            self.run = False
            # self.run_label = "Run"
        else:
            self.run = True
            # self.run_label = "Stop"

    def _run_changed(self):
        if self.run:
            self.em.connect(HeartbeatEvent, self.hb_listener)
        else:
            self.em.disconnect(HeartbeatEvent, self.hb_listener)

    def _run_default(self):
        self.hb.serve()
        return False

    def _plot_data_default(self):
        forest_grid = np.asarray(self.forest.forest_grid, dtype=int)
        data = ArrayPlotData(forest_grid=forest_grid,
                             ratio_history=self.ratio_history,
                             fire_history=self.fire_history,
                             time=self.time)
        return data

    def _forest_plot_default(self):
        plot = Plot(self.plot_data)
        plot.img_plot("forest_grid")
        plot.bounds = [0., 2.0]
        return plot

    def _time_plot_default(self):
        plot = Plot(self.plot_data)
        plot.plot(["time", "ratio_history"])
        plot.plot(["time", "fire_history"])
        return plot

    def _time_default(self):
        return np.zeros((history_length, ), dtype=int)


if __name__ == "__main__":
    # from matplotlib import pyplot as plt
    f = Forest()
    fv = ForestView(forest=f)
    fv.configure_traits()
    # for i in range(50):
    #     f.advance_one_day()
    # plt.matshow(f.forest_grid)
    # plt.show()

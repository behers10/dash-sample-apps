# -*- coding: utf-8 -*-
"""
Module doc string
"""
import pathlib
import re
from datetime import datetime
import flask
import dash
import dash_table
import matplotlib.colors as mcolors
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from dash.dependencies import Output, Input, State
from dateutil import relativedelta
from wordcloud import WordCloud, STOPWORDS
from ldacomplaints import lda_analysis


DATA_PATH = pathlib.Path(__file__).parent.resolve()
EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
FILENAME = "data/customer_complaints_narrative_sample.csv"
PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
GLOBAL_DF = pd.read_csv(DATA_PATH.joinpath(FILENAME), header=0)
"""
We are casting the whole column to datetime to make life easier in the rest of the code.
It isn't a terribly expensive operation so for the sake of tidyness we went this way.
"""
GLOBAL_DF["Date received"] = pd.to_datetime(
    GLOBAL_DF["Date received"], format="%m/%d/%Y"
)

"""
In order to make the graphs more useful we decided to prevent some words from being included
"""
ADDITIONAL_STOPWORDS = [
    "XXXX",
    "XX",
    "xx",
    "xxxx",
    "n't",
    "Trans Union",
    "BOA",
    "Citi",
    "account",
]
for stopword in ADDITIONAL_STOPWORDS:
    STOPWORDS.add(stopword)

"""
Produly written for Plotly by Vildly in 2019. info@vild.ly


The aim with this dashboard is to demonstrate how Plotly's Dash framework
can be used for NLP based data analysis. The dataset is open and contains
consumer complaints from US banks ranging from 2013 to 2017.

Users can select to run the dashboard with the whole dataset (which can be slow to run)
or a smaller subset which then is evenly and consistently sampled accordingly.

Once a datasample has been selected the user can select a bank to look into by
using the dropdown or by clicking one of the bars on the right with the top 10
banks listed by number of filed complaints. Naturally bigger banks tend to end
up in this top 10 since we do not adjust for number of customers.

Once a bank has been selected a histogram with the most commonly used words for
complaints to this specific bank is shown together with a scatter plot over all
complaints, grouped by autogenerated groups.

Users can at this point do deeper inspections into interesting formations or
clusters in the scatter plot by zooming and clicking dots.

Clicking on dots in the scatter plot will display a table showing the contents
of the selected complaint (each dot is a specific complaint).

It is worth mentioning that there is also a time frame selection slider which
allows the user to look at specific time windows if there is desire to do so.

To illustrate the usefullness of this dashboard we suggest looking at how the
wordcloud and scatter plot changes from Equifax if 2017 is included in the plots
or not.

Another potentially interesting find is that Capital One has a common word
other banks seem to lack, "Macy". It would appear that Capital One at some point
teamed up with popular retailer Macy's to offer their services. This campaing
might have been hugely popular and thus explaining it's high frequency of occurance
in complaints, or perhaps there are other reasons explaining the data.

Rergardless of what caused these two mentioned outliers, it shows how a tool
such as this can aid an analyst in finding potentially interesting things to
dig deeper into.
"""

"""
#  Somewhat helpful functions
"""


def sample_data(dataframe, float_percent):
    """
    Returns a subset of the provided dataframe.
    The sampling is evenly distributed and reproducible
    """
    print("making a local_df data sample with float_percent: %s" % (float_percent))
    return dataframe.sample(frac=float_percent, random_state=1)


def get_complaint_count_by_company(dataframe):
    """ TODO """
    company_counts = dataframe["Company"].value_counts()
    values = company_counts.keys().tolist()
    counts = company_counts.tolist()
    return values, counts


def calculate_bank_sample_data(dataframe, sample_size, time_values):
    """ TODO """
    print(
        "making bank_sample_data with sample_size count: %s and time_values: %s"
        % (sample_size, time_values)
    )
    if time_values is not None:
        min_date = time_values[0]
        max_date = time_values[1]
        dataframe = dataframe[
            (dataframe["Date received"] >= min_date)
            & (dataframe["Date received"] <= max_date)
        ]
    company_counts = dataframe["Company"].value_counts()
    company_counts_sample = company_counts[:sample_size]
    values_sample = company_counts_sample.keys().tolist()
    counts_sample = company_counts_sample.tolist()

    return values_sample, counts_sample


def make_local_df(selected_bank, time_values, n_selection):
    """ TODO """
    print("redrawing bank-wordcloud...")
    n_float = float(n_selection / 100)
    print("got time window:", str(time_values))
    print("got n_selection:", str(n_selection), str(n_float))
    # sample the dataset according to the slider
    local_df = sample_data(GLOBAL_DF, n_float)
    if time_values is not None:
        time_values = time_slider_to_date(time_values)
        local_df = local_df[
            (local_df["Date received"] >= time_values[0])
            & (local_df["Date received"] <= time_values[1])
        ]
    if selected_bank:
        local_df = local_df[local_df["Company"] == selected_bank]
        add_stopwords(selected_bank)
    return local_df


def make_marks_time_slider(mini, maxi):
    """
    A helper function to generate a dictionary that should look something like:
    {1420066800: '2015', 1427839200: 'Q2', 1435701600: 'Q3', 1443650400: 'Q4',
    1451602800: '2016', 1459461600: 'Q2', 1467324000: 'Q3', 1475272800: 'Q4',
     1483225200: '2017', 1490997600: 'Q2', 1498860000: 'Q3', 1506808800: 'Q4'}
    """
    step = relativedelta.relativedelta(months=+1)
    start = datetime(year=mini.year, month=1, day=1)
    end = datetime(year=maxi.year, month=maxi.month, day=30)
    ret = {}

    current = start
    while current <= end:
        current_str = int(current.timestamp())
        if current.month == 1:
            ret[current_str] = {
                "label": str(current.year),
                "style": {"font-weight": "bold"},
            }
        elif current.month == 4:
            ret[current_str] = {
                "label": "Q2",
                "style": {"font-weight": "lighter", "font-size": 7},
            }
        elif current.month == 7:
            ret[current_str] = {
                "label": "Q3",
                "style": {"font-weight": "lighter", "font-size": 7},
            }
        elif current.month == 10:
            ret[current_str] = {
                "label": "Q4",
                "style": {"font-weight": "lighter", "font-size": 7},
            }
        else:
            pass
        current += step
    # print(ret)
    return ret


def time_slider_to_date(time_values):
    """ TODO """
    min_date = datetime.fromtimestamp(time_values[0]).strftime("%c")
    max_date = datetime.fromtimestamp(time_values[1]).strftime("%c")
    print("Converted time_values: ")
    print("\tmin_date: ", time_values[0], "to: ", min_date)
    print("\tmax_date", time_values[1], "to: ", max_date)
    return [min_date, max_date]


def make_options_bank_drop(values):
    """
    Helper function to generate the data format the dropdown dash component wants
    """
    ret = []
    for value in values:
        ret.append({"label": value, "value": value})
    return ret


def add_stopwords(selected_bank):
    """
    In order to make a more useful NLP-data based graphs, it helps to remove
    common useless words. In this case XXXX usually represents a redacted name
    We also exlude more standard words defined in STOPWORDS which is provided by
    the Wordcloud dash component.
    """
    selected_bank_words = re.findall(r"[\w']+", selected_bank)
    for word in selected_bank_words:
        STOPWORDS.add(word.lower())

    print("Added %s stopwords:" % selected_bank)
    for word in selected_bank_words:
        print("\t", word)
    return STOPWORDS


def populate_lda_scatter(tsne_lda, lda_model, topic_num, df_dominant_topic):
    """Calculates LDA and returns figure data you can jam into a dcc.Graph()"""
    topic_top3words = [
        (i, topic)
        for i, topics in lda_model.show_topics(formatted=False)
        for j, (topic, wt) in enumerate(topics)
        if j < 3
    ]

    df_top3words_stacked = pd.DataFrame(topic_top3words, columns=["topic_id", "words"])
    df_top3words = df_top3words_stacked.groupby("topic_id").agg(", \n".join)
    df_top3words.reset_index(level=0, inplace=True)

    tsne_df = pd.DataFrame(
        {
            "tsne_x": tsne_lda[:, 0],
            "tsne_y": tsne_lda[:, 1],
            "topic_num": topic_num,
            "doc_num": df_dominant_topic["Document_No"],
        }
    )
    mycolors = np.array([color for name, color in mcolors.TABLEAU_COLORS.items()])

    # Plot and embed in ipython notebook!
    # for each topic create separate trace
    traces = []
    for topic_id in df_top3words["topic_id"]:
        # print('Topic: {} \nWords: {}'.format(idx, topic))
        tsne_df_f = tsne_df[tsne_df.topic_num == topic_id]
        cluster_name = ", ".join(
            df_top3words[df_top3words["topic_id"] == topic_id]["words"].to_list()
        )
        trace = go.Scatter(
            name=cluster_name,
            x=tsne_df_f["tsne_x"],
            y=tsne_df_f["tsne_y"],
            mode="markers",
            hovertext=tsne_df_f["doc_num"],
            marker=dict(
                size=6,
                color=mycolors[tsne_df_f["topic_num"]],  # set color equal to a variable
                colorscale="Viridis",
                showscale=False,
            ),
        )
        traces.append(trace)

    layout = go.Layout({"title": "Topic analysis using LDA"})

    return {"data": traces, "layout": layout}


def plotly_wordcloud(data_frame):
    """A wonderful function that returns figure data for three equally
    wonderful plots: wordcloud, frequency histogram and treemap"""
    complaints_text = list(data_frame["Consumer complaint narrative"].dropna().values)
    ## join all documents in corpus
    text = " ".join(list(complaints_text))

    word_cloud = WordCloud(stopwords=set(STOPWORDS), max_words=100, max_font_size=90)
    word_cloud.generate(text)

    word_list = []
    freq_list = []
    fontsize_list = []
    position_list = []
    orientation_list = []
    color_list = []

    for (word, freq), fontsize, position, orientation, color in word_cloud.layout_:
        word_list.append(word)
        freq_list.append(freq)
        fontsize_list.append(fontsize)
        position_list.append(position)
        orientation_list.append(orientation)
        color_list.append(color)

    # get the positions
    x_arr = []
    y_arr = []
    for i in position_list:
        x_arr.append(i[0])
        y_arr.append(i[1])

    # get the relative occurence frequencies
    new_freq_list = []
    for i in freq_list:
        new_freq_list.append(i * 80)

    trace = go.Scatter(
        x=x_arr,
        y=y_arr,
        textfont=dict(size=new_freq_list, color=color_list),
        hoverinfo="text",
        textposition="top center",
        hovertext=["{0} - {1}".format(w, f) for w, f in zip(word_list, freq_list)],
        mode="text",
        text=word_list,
    )

    layout = go.Layout(
        {
            "xaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 250],
            },
            "yaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 450],
            },
            "margin": dict(t=20, b=20, l=10, r=10, pad=4),
            "hovermode": "closest",
        }
    )

    wordcloud_figure_data = {"data": [trace], "layout": layout}
    word_list_top = word_list[:25]
    word_list_top.reverse()
    freq_list_top = freq_list[:25]
    freq_list_top.reverse()

    frequency_figure_data = {
        "data": [
            {
                "y": word_list_top,
                "x": freq_list_top,
                "type": "bar",
                "name": "",
                "orientation": "h",
            }
        ],
        "layout": {"height": "550", "margin": dict(t=20, b=20, l=100, r=20, pad=4)},
    }
    treemap_trace = go.Treemap(
        labels=word_list_top, parents=[""] * len(word_list_top), values=freq_list_top
    )
    treemap_layout = go.Layout({"margin": dict(t=10, b=10, l=5, r=5, pad=4)})
    treemap_figure = {"data": [treemap_trace], "layout": treemap_layout}
    return wordcloud_figure_data, frequency_figure_data, treemap_figure


"""
#  Page layout and contents

In an effort to clean up the code a bit, we decided to break it apart into
sections. For instance: LEFT_COLUMN is the input controls you see in that gray
box on the top left. The body variable is the overall structure which most other
sections go into. This just makes it ever so slightly easier to find the right 
spot to add to or change without having to count too many brackets.
"""

NAVBAR = dbc.Navbar(
    children=[
        html.A(
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row(
                [
                    dbc.Col(html.Img(src=PLOTLY_LOGO, height="30px")),
                    dbc.Col(
                        dbc.NavbarBrand("Bank Customer Complaints", className="ml-2")
                    ),
                ],
                align="center",
                no_gutters=True,
            ),
            href="https://plot.ly",
        )
    ],
    color="dark",
    dark=True,
    sticky="top",
)

LEFT_COLUMN = dbc.Jumbotron(
    [
        html.H4(children="Select bank & dataset size", className="display-5"),
        html.Hr(className="my-2"),
        html.Label("Select percentage of dataset", className="lead"),
        html.P(
            "(Lower is faster. Higher is more precise)",
            style={"fontSize": 10, "font-weight": "lighter"},
        ),
        dcc.Slider(
            id="n-selection-slider",
            min=1,
            max=100,
            step=1,
            marks={
                0: "0%",
                10: "",
                20: "20%",
                30: "",
                40: "40%",
                50: "",
                60: "60%",
                70: "",
                80: "80%",
                90: "",
                100: "100%",
            },
            value=5,
        ),
        html.Label("Select a bank", style={"marginTop": 50}, className="lead"),
        html.P(
            "(You can use the dropdown or click the barchart on the right)",
            style={"fontSize": 10, "font-weight": "lighter"},
        ),
        dcc.Dropdown(
            id="bank-drop", clearable=False, style={"marginBottom": 50, "font-size": 12}
        ),
        html.Label("Select time frame", className="lead"),
        html.Div(dcc.RangeSlider(id="time-window-slider"), style={"marginBottom": 50}),
        html.P(
            "(You can define the time frame down to month granularity)",
            style={"fontSize": 10, "font-weight": "lighter"},
        ),
    ]
)

LDA_PLOT = dcc.Loading(
    id="loading-lda-plot", children=[dcc.Graph(id="tsne-lda")], type="default"
)
LDA_TABLE = html.Div(
    id="lda-table-block",
    children=[
        dcc.Loading(
            id="loading-lda-table",
            children=[
                dash_table.DataTable(
                    id="lda-table",
                    style_cell_conditional=[
                        {
                            "if": {"column_id": "Text"},
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                            "min-width": "50%",
                        }
                    ],
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "rgb(243, 246, 251)",
                        }
                    ],
                    style_cell={
                        "padding": "16px",
                        "whiteSpace": "normal",
                        "height": "auto",
                        "max-width": "0",
                    },
                    style_header={"backgroundColor": "white", "fontWeight": "bold"},
                    style_data={"whiteSpace": "normal", "height": "auto"},
                    filter_action="native",
                    page_action="native",
                    page_current=0,
                    page_size=5,
                    columns=[],
                    data=[],
                )
            ],
            type="default",
        )
    ],
    style={"display": "none"},
)

LDA_PLOTS = [
    dbc.CardHeader(html.H5("Topic modelling using LDA")),
    dbc.CardBody(
        [
            html.P(
                "Click on a complaint point in the scatter to explore that specific complaint",
                className="mb-0",
            ),
            LDA_PLOT,
            html.Hr(),
            LDA_TABLE,
        ]
    ),
]
WORDCLOUD_PLOTS = [
    dbc.CardHeader(html.H5("Most frequently used words in complaints")),
    dbc.CardBody(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Loading(
                            id="loading-frequencies",
                            children=[dcc.Graph(id="frequency_figure")],
                            type="default",
                        )
                    ),
                    dbc.Col(
                        [
                            dcc.Tabs(
                                id="tabs",
                                children=[
                                    dcc.Tab(
                                        label="Treemap",
                                        children=[
                                            dcc.Loading(
                                                id="loading-treemap",
                                                children=[dcc.Graph(id="bank-treemap")],
                                                type="default",
                                            )
                                        ],
                                    ),
                                    dcc.Tab(
                                        label="Wordcloud",
                                        children=[
                                            dcc.Loading(
                                                id="loading-wordcloud",
                                                children=[
                                                    dcc.Graph(id="bank-wordcloud")
                                                ],
                                                type="default",
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                        md=8,
                    ),
                ]
            )
        ]
    ),
]

TOP_BANKS_PLOT = [
    dbc.CardHeader(html.H5("Top 10 banks by number of complaints")),
    dbc.CardBody(
        [
            dcc.Loading(
                id="loading-banks-hist",
                children=[dcc.Graph(id="bank-sample")],
                type="default",
            )
        ]
    ),
]

BODY = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(LEFT_COLUMN, md=4, align="center"),
                dbc.Col(dbc.Card(TOP_BANKS_PLOT), md=8),
            ],
            style={"marginTop": 30},
        ),
        dbc.Card(WORDCLOUD_PLOTS),
        dbc.Row([dbc.Col([dbc.Card(LDA_PLOTS)])], style={"marginTop": 50}),
    ],
    className="mt-12",
)


SERVER = flask.Flask(__name__)
APP = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], server=SERVER)
APP.layout = html.Div(children=[NAVBAR, BODY])

"""
#  Callbacks
"""


@APP.callback(
    [
        Output("time-window-slider", "marks"),
        Output("time-window-slider", "min"),
        Output("time-window-slider", "max"),
        Output("time-window-slider", "step"),
        Output("time-window-slider", "value"),
    ],
    [Input("n-selection-slider", "value")],
)
def populate_time_slider(value):
    """
    Depending on our dataset, we need to populate the time-slider
    with different ranges. This function does that and returns the
    needed data to the time-window-slider.
    """
    value += 0
    min_date = GLOBAL_DF["Date received"].min()
    max_date = GLOBAL_DF["Date received"].max()

    marks = make_marks_time_slider(min_date, max_date)
    min_epoch = list(marks.keys())[0]
    max_epoch = list(marks.keys())[-1]

    return (
        marks,
        min_epoch,
        max_epoch,
        (max_epoch - min_epoch) / (len(list(marks.keys())) * 3),
        [min_epoch, max_epoch],
    )


@APP.callback(
    Output("bank-drop", "options"),
    [Input("time-window-slider", "value"), Input("n-selection-slider", "value")],
)
def populate_bank_dropdown(time_values, n_value):
    """ TODO """
    print("bank-drop: TODO USE THE TIME VALUES AND N-SLIDER TO LIMIT THE DATASET")
    if time_values is not None:
        pass
    n_value += 1
    bank_names, counts = get_complaint_count_by_company(GLOBAL_DF)
    counts.append(1)
    return make_options_bank_drop(bank_names)


@APP.callback(
    Output("bank-sample", "figure"),
    [Input("n-selection-slider", "value"), Input("time-window-slider", "value")],
)
def update_bank_sample_plot(n_value, time_values):
    """ TODO """
    print("redrawing bank-sample...")
    print("\tn is:", n_value)
    print("\ttime_values is:", time_values)
    if time_values is None:
        return {}
    n_float = float(n_value / 100)
    bank_sample_count = 10
    local_df = sample_data(GLOBAL_DF, n_float)
    min_date, max_date = time_slider_to_date(time_values)
    values_sample, counts_sample = calculate_bank_sample_data(
        local_df, bank_sample_count, [min_date, max_date]
    )
    data = [
        {
            "x": values_sample,
            "y": counts_sample,
            "text": values_sample,
            "textposition": "auto",
            "type": "bar",
            "name": "",
        }
    ]
    layout = {
        "autosize": False,
        "margin": dict(t=10, b=10, l=40, r=0, pad=4),
        "xaxis": {"showticklabels": False},
    }
    print("redrawing bank-sample...done")
    return {"data": data, "layout": layout}


@APP.callback(
    [
        Output("lda-table", "data"),
        Output("lda-table", "columns"),
        Output("tsne-lda", "figure"),
    ],
    [
        Input("bank-drop", "value"),
        Input("time-window-slider", "value"),
        Input("n-selection-slider", "value"),
    ],
)
def update_lda_table(value_drop, time_values, n_selection):
    """ TODO """
    local_df = make_local_df(value_drop, time_values, n_selection)
    complaints_text = list(local_df["Consumer complaint narrative"].dropna().values)
    if len(complaints_text) <= 10:  # we cannot do LDA on less than 11 complaints
        return [[], [], {}]
    tsne_lda, lda_model, topic_num, df_dominant_topic = lda_analysis(
        complaints_text, list(STOPWORDS)
    )

    lda_scatter_figure = populate_lda_scatter(
        tsne_lda, lda_model, topic_num, df_dominant_topic
    )

    columns = [{"name": i, "id": i} for i in df_dominant_topic.columns]
    data = df_dominant_topic.to_dict("records")

    return (data, columns, lda_scatter_figure)


def precompute_all_lda():
    """ QD function for precomputing all necessary LDA results
     to allow much faster load times when the app runs. """
    min_date = GLOBAL_DF["Date received"].min()
    max_date = GLOBAL_DF["Date received"].max()
    marks = make_marks_time_slider(min_date, max_date)
    min_epoch = list(marks.keys())[0]
    max_epoch = list(marks.keys())[-1]
    bank_names, counts = get_complaint_count_by_company(GLOBAL_DF)
    counts += 1
    results = {}
    time_values = [min_epoch, max_epoch]
    n_selection = 100
    file = open("precomupted", "w")
    file.close()
    for bank in bank_names:
        file = open("precomupted", "a")
        print("crunching LDA for: ", bank)
        results[bank] = update_lda_table(bank, time_values, n_selection)
        file.write(str(results))
        file.close()
    print(results)


@APP.callback(
    [
        Output("bank-wordcloud", "figure"),
        Output("frequency_figure", "figure"),
        Output("bank-treemap", "figure"),
    ],
    [
        Input("bank-drop", "value"),
        Input("time-window-slider", "value"),
        Input("n-selection-slider", "value"),
    ],
)
def update_wordcloud_plot(value_drop, time_values, n_selection):
    """ TODO """
    local_df = make_local_df(value_drop, time_values, n_selection)
    wordcloud, frequency_figure, treemap = plotly_wordcloud(local_df)
    print("redrawing bank-wordcloud...done")
    return (wordcloud, frequency_figure, treemap)


@APP.callback(
    [Output("lda-table", "filter_query"), Output("lda-table-block", "style")],
    [Input("tsne-lda", "clickData")],
    [State("lda-table", "filter_query")],
)
def filter_table_on_scatter_click(tsne_click, current_filter):
    """ TODO """
    if tsne_click is not None:
        selected_complaint = tsne_click["points"][0]["hovertext"]
        if current_filter != "":
            filter_query = (
                "({Document_No} eq "
                + str(selected_complaint)
                + ") || ("
                + current_filter
                + ")"
            )
        else:
            filter_query = "{Document_No} eq " + str(selected_complaint)
        # ({avf} < 12000) && ({avf} >= 10000)
        print("current_filter", current_filter)
        return (filter_query, {"display": "block"})
    return ["", {"display": "none"}]


@APP.callback(Output("bank-drop", "value"), [Input("bank-sample", "clickData")])
def update_bank_drop_on_click(value):
    """ TODO """
    if value is not None:
        selected_bank = value["points"][0]["x"]
        return selected_bank
    return "EQUIFAX, INC."


if __name__ == "__main__":
    # precompute_all_lda()
    APP.run_server(debug=True)

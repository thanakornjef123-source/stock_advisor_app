# -*- coding: utf-8 -*-
"""
Chart helpers.

Plotly defaults look like a report. A trading screen needs a crosshair that
labels both axes, quick range buttons, an optional log scale and candles that
read cleanly at small sizes. These wrappers apply that treatment consistently.
"""
import numpy as np
import plotly.graph_objects as go

from core import theme as T

RANGE_BUTTONS = dict(
    buttons=[dict(count=1, label="1M", step="month", stepmode="backward"),
             dict(count=3, label="3M", step="month", stepmode="backward"),
             dict(count=6, label="6M", step="month", stepmode="backward"),
             dict(count=1, label="YTD", step="year", stepmode="todate"),
             dict(count=1, label="1Y", step="year", stepmode="backward"),
             dict(step="all", label="ALL")],
    bgcolor=T.PANEL, activecolor=T.ACCENT,
    bordercolor=T.BORDER, borderwidth=1,
    font=dict(family=T.MONO, size=10, color=T.MUTED),
    x=0, y=1.16, xanchor="left", yanchor="top",
)


def surface(fig):
    """A faint plot fill so the chart reads as a panel, not a hole in the page."""
    fig.update_layout(plot_bgcolor="rgba(255,255,255,0.012)",
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def crosshair(fig, y_prefix="", y_suffix=""):
    """Spike lines on both axes with a value label, the way a terminal does it."""
    fig.update_xaxes(
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikecolor=T.MUTED, spikethickness=1, spikedash="dot")
    fig.update_yaxes(
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikecolor=T.MUTED, spikethickness=1, spikedash="dot",
        tickprefix=y_prefix, ticksuffix=y_suffix)
    fig.update_layout(hovermode="x unified", spikedistance=-1, hoverdistance=60)
    return surface(fig)


def time_series(fig, *, height=380, y_title="", ranges=True, log=False,
                legend=True, zero_line=False, y_suffix=""):
    """Standard treatment for anything plotted against a date axis."""
    fig.update_layout(
        height=height, yaxis_title=y_title,
        showlegend=legend,
        margin=dict(l=8, r=8, t=44 if ranges else 24, b=8),
        yaxis=dict(type="log" if log else "linear"))
    if ranges:
        fig.update_xaxes(rangeselector=RANGE_BUTTONS, rangeslider=dict(visible=False))
    if zero_line:
        fig.add_hline(y=0, line_dash="dot", line_color=T.BORDER, line_width=1)
    return crosshair(fig, y_suffix=y_suffix)


def line(x, y, name, colour=None, width=2.0, fill=False, dash=None):
    c = colour or T.ACCENT
    rgb = _rgb(c)
    return go.Scatter(
        x=x, y=y, name=name, mode="lines",
        line=dict(color=c, width=width, dash=dash),
        fill="tozeroy" if fill else None,
        fillcolor=f"rgba({rgb},0.08)" if fill else None,
        hovertemplate="%{y:,.2f}<extra>" + name + "</extra>")


def candles(d, name="Price"):
    return go.Candlestick(
        x=d["date"], open=d["open"], high=d["high"], low=d["low"], close=d["close"],
        name=name, showlegend=False,
        increasing=dict(line=dict(color=T.UP, width=0.9), fillcolor=T.UP),
        decreasing=dict(line=dict(color=T.DOWN, width=0.9), fillcolor=T.DOWN),
        whiskerwidth=0.25)


def volume_bars(d):
    colours = np.where(d["close"] >= d["open"],
                       "rgba(38,166,154,0.45)", "rgba(239,83,80,0.45)")
    return go.Bar(x=d["date"], y=d["total_volume"], name="Volume",
                  marker_color=colours, marker_line_width=0, showlegend=False,
                  hovertemplate="%{y:,.0f}<extra>Volume</extra>")


def hbar(x, y, *, positive_negative=True, colour=None, suffix="%", height=None,
         x_title=""):
    """Horizontal bars — the shape used for sector and contribution views."""
    if positive_negative:
        cols = [T.UP if v >= 0 else T.DOWN for v in x]
    else:
        cols = colour or T.ACCENT
    fig = go.Figure(go.Bar(
        x=x, y=y, orientation="h", marker_color=cols, marker_line_width=0,
        text=[f"{v:+.1f}{suffix}" if positive_negative else f"{v:,.0f}" for v in x],
        textposition="outside", textfont=dict(family=T.MONO, size=10),
        cliponaxis=False))
    if positive_negative:
        fig.add_vline(x=0, line_color=T.BORDER, line_width=1)
    fig.update_layout(height=height or max(260, 26 * len(y)),
                      xaxis_title=x_title, yaxis_title="",
                      margin=dict(l=8, r=64, t=18, b=8), showlegend=False)
    return surface(fig)


def _rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))

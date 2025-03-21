from datetime import UTC, datetime, timezone
from io import BytesIO
from typing import Optional

import matplotlib.pyplot as plt
import seaborn as sns


def convert_time(
    time_to_convert: datetime,
    to_timezone: timezone = UTC,
    is_offset_naive: bool = True,
) -> datetime:
    """Convert provided time to desired timezone."""
    if not time_to_convert.tzinfo:
        time_to_convert = time_to_convert.replace(tzinfo=UTC)
    time = time_to_convert.astimezone(to_timezone)
    return time.replace(tzinfo=None) if is_offset_naive else time


def utcnow(is_timezone: bool = False):
    """Get current datetime object."""
    now = datetime.now().astimezone(UTC)
    return now if is_timezone else now.replace(tzinfo=None)


def custom_urljoin(base_url: str, path: str) -> str:
    """Join two url parts."""
    return '{}/{}'.format(base_url.rstrip('/'), path.lstrip('/'))


def make_pie_chart(
    labels: list[str],
    data: list[float],
    palette: str = 'pastel',
    title: Optional[str] = None,
    legend_title: Optional[str] = None,
) -> bytes:
    """Make pie chart from data and labels."""
    colors = sns.color_palette(palette, n_colors=len(data))
    legend_height = max(4, len(labels) * 0.3)
    fig, ax = plt.subplots(figsize=(8, legend_height))
    wedges, _, autotexts = ax.pie(
        data, labels=[None] * len(data), colors=colors, autopct='%1.1f%%'
    )

    fig.subplots_adjust(left=0, right=0.75)
    legend_ax = fig.add_axes([0.60, 0.2, 0.25, 0.6])
    legend_ax.axis('off')

    legend_labels = [f'{label}: {value:.2f}' for label, value in zip(labels, data)]
    legend_ax.legend(wedges, legend_labels, title=legend_title, loc='center', frameon=False, title_fontsize='medium')
    if title:
        ax.set_title(title)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)

    image_bytes = buf.getvalue()
    buf.close()
    return image_bytes

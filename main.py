from bs4 import BeautifulSoup
import re
import os
import requests
from typing import List
import pandas as pd
from tqdm import tqdm
from matplotlib import pyplot as plt
import japanize_matplotlib
import datetime
import collections

URL = "https://kakaku.com/pc/pc-memory/itemlist.aspx?pdf_Spec105=1&pdf_so=e2&pdf_vi=d&pdf_pg={int}"
DIR = os.path.dirname(__file__)
JP_SPACE = '　'
DF_COL = ['Manufacturer',
          'ProductName',
          'ReleaseYear',
          'ReleaseMonth',
          'ReleaseDay',
          'DDR_ver',
          'Bandwidth']
DDR2_PIN = 240
DDR3_PIN = 240
DDR4_PIN = 288
DDR5_PIN = 288


def gen_URL(id: int) -> str:
    return f"https://kakaku.com/pc/pc-memory/itemlist.aspx?pdf_Spec105=1&pdf_so=e2&pdf_vi=d&pdf_pg={id}"


def soup_htmlPage(url: str) -> str:
    texted = requests.get(url).text
    souped = BeautifulSoup(texted, "html.parser")
    return souped


def get_resultTable(souped_html: BeautifulSoup) -> pd.DataFrame:
    df = pd.DataFrame(columns=DF_COL)
    # manifacture, name, etc
    item_names = souped_html.select("td[class=\"ckitemLink\"]")
    # release data str
    item_release = souped_html.select("td[class=\"swdate1\"]")
    # detail specs
    item_spec_detail = souped_html.select("div[class=\"ckitemSpecInnr\"]")

    item_count = len(item_names)
    for i in range(item_count):
        # parse each info
        item_names_str = item_names[i].text
        release_str = item_release[i].text
        # ex: ドスパラ 【直販モデル】　D4N3200-16G1A2 [SODIMM DDR4 PC4-25600 16GB]
        print(item_names_str)
        manufacturer = re.search(r"(^.*)\u3000", item_names_str).group(1)
        if manufacturer != "ノーブランド":
            productname = re.search(
                r"\u3000(.*) [\[\(]", item_names_str).group(1)
        else:
            productname = None
        # PC{DDR_VERSION}-{BAND_WIDTH}の体裁でないものは拒否
        specs = re.search(r".* ?PC([0-9])L?-([0-9]+) ?.*", item_names_str)
        if specs == None:
            continue
        ddr_ver = int(specs.group(1))
        band_width = int(specs.group(2))
        release_date = re.search(r"([0-9]+)/([0-9]+)/ ?([0-9]+)", release_str)
        yyyy = int(release_date.group(1))
        mm = int(release_date.group(2))
        dd = int(release_date.group(3))

        append_df = pd.DataFrame(data=[[manufacturer,
                                        productname,
                                        yyyy,
                                        mm,
                                        dd,
                                        ddr_ver,
                                        band_width]],
                                 columns=DF_COL)
        df = pd.concat([df, append_df], ignore_index=True)
    return df


def scrape():
    id = range(1, 48)  # 2023/20/17現在，最大47ページ
    df = pd.DataFrame(columns=DF_COL)
    dt_now = datetime.datetime.now()
    for i in id:
        print(f"{i}")
        url = gen_URL(i)
        soup = soup_htmlPage(url)
        append_df = get_resultTable(soup)
        df = pd.concat([df, append_df], ignore_index=True)
    df.to_csv(f"{DIR}/{dt_now.year}{dt_now.month}{dt_now.day}{dt_now.hour}.csv")
    target_year_products = df.query("2020 <= ReleaseYear <= 2022")
    target_year_products.to_csv(f"{DIR}/2020_2022.csv")


def read_localCsv(filepath: str) -> pd.DataFrame:
    return pd.read_csv(filepath)


def create_date_band_table(df: pd.DataFrame, ddr_ver: int) -> List:
    ddr_div = df[df["DDR_ver"] == ddr_ver]
    ddr_div = ddr_div.reset_index(drop=True)
    date_band = pd.DataFrame()
    date_band["Name"] = ddr_div["ProductName"]
    date_band["Band"] = ddr_div["Bandwidth"] / 1000  # MB/s -> GB/s
    date_band["Date"] = pd.to_datetime(ddr_div["ReleaseYear"].astype(str)+'-' +
                                       ddr_div["ReleaseMonth"].astype(str)+'-' +
                                       ddr_div["ReleaseDay"].astype(str),
                                       format="%Y-%m-%d")
    return date_band


if __name__ == "__main__":
    # scrape()
    df = read_localCsv(f"{DIR}/202310174.csv")
    mfacs = df[["ReleaseYear", "ReleaseMonth",
                "ReleaseDay", "DDR_ver", "Bandwidth"]]

    ddr2 = create_date_band_table(df, 2)
    ddr3 = create_date_band_table(df, 3)
    ddr4 = create_date_band_table(df, 4)
    ddr5 = create_date_band_table(df, 5)

    plt.rcParams['figure.subplot.bottom'] = 0.15  # xラベル見切れ対処
    scat_size = 8
    # plt.scatter(ddr2["Date"], ddr2["Band"], label="DDR2", s=scat_size)
    # plt.scatter(ddr3["Date"], ddr3["Band"], label="DDR3", s=scat_size)
    # plt.scatter(ddr4["Date"], ddr4["Band"], label="DDR4", s=scat_size)
    # plt.scatter(ddr5["Date"], ddr5["Band"], label="DDR5", s=scat_size)
    plt.scatter(ddr2["Band"] / DDR2_PIN * 1000,
                ddr2["Band"],
                label="DDR2",
                s=scat_size)
    plt.scatter(ddr3["Band"] / DDR3_PIN * 1000,
                ddr3["Band"],
                label="DDR3",
                s=scat_size)
    plt.scatter(ddr4["Band"] / DDR4_PIN * 1000,
                ddr4["Band"],
                label="DDR4",
                s=scat_size)
    plt.scatter(ddr5["Band"] / DDR5_PIN * 1000,
                ddr5["Band"],
                label="DDR5",
                s=scat_size)
    plt.title("メモリの種類とバンド幅・ピンごとの転送速度の関係")
    plt.legend()
    plt.grid(linewidth=0.5)
    plt.yscale("log", base=2)
    plt.ylabel("バンド幅[GB/s]")
    plt.xticks(rotation=30)
    plt.xscale("log", base=2)
    plt.xlabel("ピン1つあたりの転送速度[MB/s]")

    plt.savefig(f"{DIR}/Band_pin__memoryType_wholeYear.png", dpi=900)

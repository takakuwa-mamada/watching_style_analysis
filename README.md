# watching_style_analysis
ファイル名を指定して実行

python topic.py --files "data~~.csv" --wc-top-k 10 --wc-bin-pad 1

python topic.py --files "data/football/PSG_IntelMiami_France.csv,data/football/Dodgers_WhiteSox_Japan.csv"

上位いくつのトピックでワードクラウドを作るか
python topic.py --wc-top-k 8

ワードクラウドに使う時間窓
python topic.py --wc-bin-pad 1


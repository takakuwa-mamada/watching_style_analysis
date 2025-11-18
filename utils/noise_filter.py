"""
Noise Filter Utility

コメントとN-gramからノイズを除去して、イベント検出の品質を向上させる
"""

import re
from collections import Counter
import numpy as np


class NoiseFilter:
    """ノイズフィルタリングクラス"""
    
    def __init__(self):
        # ノイズパターン定義
        self.noise_patterns = [
            r'^k{3,}$',              # kkkkkk
            r'^w{3,}$',              # wwwwww
            r'^laugh( laugh)*$',     # laugh laugh laugh
            r'^lol( lol)*$',         # lol lol lol
            r'^clap( clap)*$',       # clap clap clap
            r'^haha( haha)*$',       # haha haha
            r'^jaja( jaja)*$',       # jaja jaja (スペイン語)
            r'^[0-9]+$',             # 数字のみ
            r'^[!?。、]+$',          # 記号のみ
            r'^emoji_\w+$',          # Emoji単体
            r'^[\s]+$',              # 空白のみ
            r'^\.+$',                # ピリオドのみ
            r'^-+$',                 # ハイフンのみ
            r'^_+$',                 # アンダースコアのみ
        ]
        
        # 言語別ストップワード
        self.stopwords = {
            'ja': set(['の', 'は', 'を', 'が', 'に', 'で', 'と', 'から', 'まで', 'より', 
                      'も', 'な', 'だ', 'ある', 'いる', 'する', 'なる', 'です', 'ます']),
            'en': set(['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                      'could', 'should', 'may', 'might', 'can', 'of', 'in', 'to', 
                      'for', 'on', 'at', 'by', 'with', 'from', 'as']),
            'es': set(['el', 'la', 'de', 'en', 'y', 'a', 'los', 'las', 'del', 'un', 
                      'una', 'es', 'por', 'para', 'con', 'no', 'se', 'su']),
            'pt': set(['o', 'a', 'de', 'em', 'e', 'do', 'da', 'para', 'com', 'no', 
                      'um', 'uma', 'os', 'as', 'dos', 'das']),
        }
        
        # 低品質パターン (部分一致)
        self.low_quality_substrings = [
            'wwww',
            'kkkk',
            'hhhh',
            'llll',
            '!!!!',
            '????',
            '....',
        ]
    
    def is_noise(self, text):
        """
        テキストがノイズかどうか判定
        
        Args:
            text: 判定するテキスト
            
        Returns:
            bool: ノイズならTrue
        """
        if not isinstance(text, str):
            return True
        
        text_clean = text.strip().lower()
        
        # 空文字
        if len(text_clean) == 0:
            return True
        
        # 正規表現マッチ
        for pattern in self.noise_patterns:
            if re.match(pattern, text_clean):
                return True
        
        # 1文字 (ただし意味のある文字は除外)
        if len(text_clean) == 1:
            # 数字、記号のみはノイズ
            if text_clean in '0123456789!?。、.,;:-_=+*/#@$%^&()[]{}':
                return True
        
        # 同じ文字の繰り返し (80%以上)
        if len(text_clean) > 1:
            char_counts = Counter(text_clean)
            max_char_ratio = char_counts.most_common(1)[0][1] / len(text_clean)
            if max_char_ratio > 0.8:
                return True
        
        # 低品質な部分文字列を含む
        for substring in self.low_quality_substrings:
            if substring in text_clean:
                return True
        
        return False
    
    def is_stopword(self, word, lang='en'):
        """
        単語がストップワードかどうか判定
        
        Args:
            word: 判定する単語
            lang: 言語コード ('ja', 'en', 'es', 'pt')
            
        Returns:
            bool: ストップワードならTrue
        """
        if lang in self.stopwords:
            return word.lower() in self.stopwords[lang]
        return False
    
    def filter_comments(self, comments):
        """
        コメントリストからノイズを除去
        
        Args:
            comments: コメントのリスト
            
        Returns:
            list: フィルタリングされたコメント
        """
        return [c for c in comments if not self.is_noise(c)]
    
    def filter_ngrams(self, ngrams):
        """
        N-gramリストからノイズを除去
        
        Args:
            ngrams: N-gramのリスト
            
        Returns:
            list: フィルタリングされたN-gram
        """
        filtered = []
        for ngram in ngrams:
            # 各単語がノイズでないかチェック
            words = str(ngram).split()
            
            # 全ての単語がノイズ → 除外
            if all(self.is_noise(w) for w in words):
                continue
            
            # 少なくとも1つは意味のある単語がある → 保持
            if any(not self.is_noise(w) for w in words):
                filtered.append(ngram)
        
        return filtered
    
    def score_topic_quality(self, topic_words):
        """
        トピックの品質スコアリング (0-1)
        
        Args:
            topic_words: トピックの単語リスト
            
        Returns:
            float: 品質スコア (0-1)
        """
        if not topic_words or len(topic_words) == 0:
            return 0.0
        
        # 文字列のリストに変換
        topic_words = [str(w) for w in topic_words]
        
        # 1. ノイズ単語の割合
        noise_count = sum(1 for w in topic_words if self.is_noise(w))
        noise_ratio = noise_count / len(topic_words)
        
        # 2. 多様性 (ユニーク単語の割合)
        unique_ratio = len(set(topic_words)) / len(topic_words)
        
        # 3. 平均単語長
        avg_length = np.mean([len(w) for w in topic_words if len(w) > 0])
        length_score = min(avg_length / 10, 1.0)  # 長い方が良い (10文字以上で満点)
        
        # 4. 意味のある単語の割合
        meaningful_count = sum(1 for w in topic_words 
                             if not self.is_noise(w) and len(w) > 2)
        meaningful_ratio = meaningful_count / len(topic_words)
        
        # 総合スコア (重み付け平均)
        quality = (
            (1 - noise_ratio) * 0.3 +     # ノイズが少ない (30%)
            unique_ratio * 0.2 +           # 多様性がある (20%)
            length_score * 0.2 +           # 単語が長い (20%)
            meaningful_ratio * 0.3         # 意味のある単語が多い (30%)
        )
        
        return quality
    
    def filter_events_by_quality(self, events, min_quality=0.3):
        """
        イベントを品質スコアでフィルタリング
        
        Args:
            events: イベントのリスト (各イベントは 'top_words' を持つ)
            min_quality: 最小品質スコア
            
        Returns:
            list: フィルタリングされたイベント
        """
        filtered = []
        
        for event in events:
            if 'top_words' not in event:
                continue
            
            top_words = event['top_words']
            if isinstance(top_words, str):
                top_words = top_words.split()
            
            quality = self.score_topic_quality(top_words)
            event['quality_score'] = quality
            
            if quality >= min_quality:
                filtered.append(event)
        
        return filtered
    
    def get_statistics(self, texts):
        """
        テキストのノイズ統計を取得
        
        Args:
            texts: テキストのリスト
            
        Returns:
            dict: 統計情報
        """
        total = len(texts)
        noise_count = sum(1 for t in texts if self.is_noise(t))
        
        stats = {
            'total': total,
            'noise': noise_count,
            'clean': total - noise_count,
            'noise_ratio': noise_count / total if total > 0 else 0,
            'clean_ratio': (total - noise_count) / total if total > 0 else 0,
        }
        
        return stats


# 使用例
if __name__ == '__main__':
    # テスト
    noise_filter = NoiseFilter()
    
    # テストケース
    test_comments = [
        "Great goal!",           # OK
        "kkkkkkkk",              # Noise
        "wwwwwwww",              # Noise
        "laugh laugh laugh",     # Noise
        "Nice play",             # OK
        "!!!!!",                 # Noise
        "12345",                 # Noise
        "Brasil vs Japan",       # OK
        "...",                   # Noise
        "ゴール!",               # OK
        "草草草草",              # Noise (wwww)
    ]
    
    print("Testing Noise Filter:")
    print("=" * 50)
    
    for comment in test_comments:
        is_noise = noise_filter.is_noise(comment)
        status = "❌ NOISE" if is_noise else "✅ CLEAN"
        print(f"{status}: {comment}")
    
    print("\n" + "=" * 50)
    
    # フィルタリング
    filtered = noise_filter.filter_comments(test_comments)
    print(f"\nOriginal: {len(test_comments)} comments")
    print(f"Filtered: {len(filtered)} comments")
    print(f"Removed: {len(test_comments) - len(filtered)} comments ({(len(test_comments) - len(filtered)) / len(test_comments) * 100:.1f}%)")
    
    # 統計
    stats = noise_filter.get_statistics(test_comments)
    print(f"\nStatistics:")
    print(f"  Total: {stats['total']}")
    print(f"  Noise: {stats['noise']} ({stats['noise_ratio']:.1%})")
    print(f"  Clean: {stats['clean']} ({stats['clean_ratio']:.1%})")
    
    # トピック品質スコアリング
    print("\n" + "=" * 50)
    print("Topic Quality Scoring:")
    
    test_topics = [
        ['goal', 'amazing', 'brasil', 'soccer'],           # High quality
        ['kkkk', 'wwww', 'lol'],                           # Low quality
        ['player', 'foul', 'referee', 'yellow card'],      # High quality
        ['1', '2', '3', '!'],                              # Low quality
    ]
    
    for i, topic in enumerate(test_topics, 1):
        score = noise_filter.score_topic_quality(topic)
        quality = "✅ HIGH" if score >= 0.7 else "⚠️ MEDIUM" if score >= 0.4 else "❌ LOW"
        print(f"Topic {i}: {quality} (score={score:.3f}) - {topic}")

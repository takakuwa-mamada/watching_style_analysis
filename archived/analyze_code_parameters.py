# Phase 0: 現状の完全把握
# Step 0.2: 現在のコードパラメータを抽出

import re
from pathlib import Path
import json

def extract_parameters_from_code():
    """event_comparison.pyから現在のパラメータを抽出"""
    
    print("="*60)
    print("Extracting Current Code Parameters")
    print("="*60)
    
    code_file = Path('event_comparison.py')
    
    if not code_file.exists():
        print(f"❌ File not found: {code_file}")
        return None
    
    print(f"\n[1/4] Reading {code_file}...")
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    print(f"✅ Loaded {len(code)} characters")
    
    parameters = {
        "file": str(code_file),
        "extraction_date": "2025-11-10",
        "tfidf_params": {},
        "weights": {},
        "bertopic_params": {},
        "other_params": {}
    }
    
    # 2. TfidfVectorizer のパラメータを抽出
    print("\n[2/4] Extracting TfidfVectorizer parameters...")
    
    # extract_ngram_topics_direct 関数内の TfidfVectorizer を探す
    # 行番号687付近
    pattern = r'vectorizer\s*=\s*TfidfVectorizer\s*\((.*?)\)'
    matches = re.findall(pattern, code, re.DOTALL)
    
    if matches:
        print(f"  Found {len(matches)} TfidfVectorizer instance(s)")
        
        for i, match in enumerate(matches, 1):
            print(f"\n  Instance {i}:")
            
            # パラメータを抽出
            param_pattern = r'(\w+)\s*=\s*([^,\)]+)'
            params = re.findall(param_pattern, match)
            
            instance_params = {}
            for param, value in params:
                value_clean = value.strip()
                print(f"    {param:20s} = {value_clean}")
                instance_params[param] = value_clean
            
            parameters["tfidf_params"][f"instance_{i}"] = instance_params
    else:
        print("  ⚠️  No TfidfVectorizer found")
    
    # 3. 重み係数を探す
    print("\n[3/4] Extracting similarity weights...")
    
    # combined_score の計算部分を探す
    # パターン: 数値 * component_name
    weight_patterns = {
        'embedding': r'([\d.]+)\s*\*\s*embedding',
        'lexical': r'([\d.]+)\s*\*\s*lexical',
        'topic': r'([\d.]+)\s*\*\s*topic',
        'temporal': r'([\d.]+)\s*\*\s*temporal',
    }
    
    found_weights = False
    for component, pattern in weight_patterns.items():
        matches = re.findall(pattern, code, re.IGNORECASE)
        if matches:
            # 最初に見つかった値を使用
            weight = matches[0]
            print(f"  {component:20s}: {weight}")
            parameters["weights"][component] = float(weight)
            found_weights = True
    
    if not found_weights:
        print("  ⚠️  No explicit weights found")
        print("  (Weights may be computed dynamically)")
    
    # 4. BERTopic/HDBSCAN/UMAPのパラメータ
    print("\n[4/4] Extracting clustering parameters...")
    
    clustering_params = {
        'min_cluster_size': r'min_cluster_size\s*=\s*(\d+)',
        'min_samples': r'min_samples\s*=\s*(\d+)',
        'n_neighbors': r'n_neighbors\s*=\s*(\d+)',
        'n_components': r'n_components\s*=\s*(\d+)',
        'min_topic_size': r'min_topic_size\s*=\s*(\d+)',
    }
    
    for param, pattern in clustering_params.items():
        matches = re.findall(pattern, code)
        if matches:
            # 最初に見つかった値を使用
            value = matches[0]
            print(f"  {param:20s}: {value}")
            parameters["bertopic_params"][param] = int(value)
    
    # 5. その他の重要なパラメータ
    print("\n[Other Important Parameters]")
    
    other_patterns = {
        'peak_pad': r'peak_pad["\']?\s*[:\]]\s*(\d+)',
        'embedding_match_th': r'embedding_match_th["\']?\s*[:\]]\s*([\d.]+)',
        'top_k_ngrams': r'top_k\s*=\s*(\d+)',
    }
    
    for param, pattern in other_patterns.items():
        matches = re.findall(pattern, code)
        if matches:
            value = matches[0]
            print(f"  {param:20s}: {value}")
            parameters["other_params"][param] = value
    
    # 保存
    print("\n" + "="*60)
    print("Saving parameters...")
    print("="*60)
    
    output_dir = Path('output/snapshots')
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'code_parameters_baseline.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(parameters, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Parameters saved: {json_file}")
    
    # 人間が読める形式でも保存
    txt_file = output_dir / 'code_parameters_baseline.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("Code Parameters Extraction (2025-11-10)\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Source file: {parameters['file']}\n")
        f.write(f"Date: {parameters['extraction_date']}\n\n")
        
        f.write("[TfidfVectorizer Parameters]\n")
        for instance, params in parameters['tfidf_params'].items():
            f.write(f"  {instance}:\n")
            for param, value in params.items():
                f.write(f"    {param:20s} = {value}\n")
            f.write("\n")
        
        if parameters['weights']:
            f.write("[Similarity Weights]\n")
            for component, weight in parameters['weights'].items():
                f.write(f"  {component:20s}: {weight}\n")
            f.write("\n")
        
        if parameters['bertopic_params']:
            f.write("[BERTopic/HDBSCAN/UMAP Parameters]\n")
            for param, value in parameters['bertopic_params'].items():
                f.write(f"  {param:20s}: {value}\n")
            f.write("\n")
        
        if parameters['other_params']:
            f.write("[Other Parameters]\n")
            for param, value in parameters['other_params'].items():
                f.write(f"  {param:20s}: {value}\n")
    
    print(f"✅ Human-readable report saved: {txt_file}")
    
    print("\n" + "="*60)
    print("✅ Parameter extraction completed!")
    print("="*60)
    
    return parameters

def analyze_parameters(parameters):
    """抽出したパラメータを分析"""
    
    if not parameters:
        return
    
    print("\n" + "="*60)
    print("Parameter Analysis")
    print("="*60)
    
    # TfidfVectorizerの分析
    if parameters.get('tfidf_params'):
        print("\n[TfidfVectorizer Analysis]")
        for instance, params in parameters['tfidf_params'].items():
            max_features = params.get('max_features', 'Not specified')
            print(f"  {instance}: max_features = {max_features}")
            
            if max_features == '2000':
                print("    💡 Recommendation: Increase to 3000 for better topic coverage")
    
    # 重みの分析
    if parameters.get('weights'):
        print("\n[Weight Analysis]")
        total_weight = sum(parameters['weights'].values())
        print(f"  Total weight: {total_weight:.2f}")
        
        if abs(total_weight - 1.0) > 0.01:
            print("  ⚠️  Weights do not sum to 1.0")
        
        for component, weight in parameters['weights'].items():
            percentage = weight / total_weight * 100
            print(f"  {component:20s}: {weight:.2f} ({percentage:5.1f}%)")
    
    print("\n✅ Analysis completed!")

if __name__ == '__main__':
    parameters = extract_parameters_from_code()
    
    if parameters:
        analyze_parameters(parameters)
        print("\n✅ Ready for optimization!")

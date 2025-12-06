import pandas as pd
import json
import re
from collections import Counter
from transformers import pipeline

print("Loading model...")
pipe = pipeline(
    "text-generation",
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    max_new_tokens=100,
    temperature=0.3,
    do_sample=True
)
print("Model loaded!\n")

df = pd.read_csv('yelp.csv')
df_sample = df.sample(n=200, random_state=42).reset_index(drop=True)
print(f"Loaded {len(df_sample)} reviews\n")


def prompt_basic(review):
    prompt = f"""<|system|>
You are a rating classifier. Rate reviews 1-5 stars and return only JSON.</s>
<|user|>
Rate this review from 1 to 5 stars.

Review: "{review[:200]}"

Return only JSON:
{{"predicted_stars": 4, "explanation": "reason"}}</s>
<|assistant|>"""
    
    result = pipe(prompt, max_new_tokens=100)
    return result[0]['generated_text'].split('<|assistant|>')[-1]


def prompt_guided(review):
    prompt = f"""<|system|>
You are a rating classifier. Use sentiment keywords to rate 1-5 stars and return only JSON.</s>
<|user|>
Rate this review using keywords:

5 stars: amazing, excellent, perfect, loved
4 stars: good, nice, great, enjoyed  
3 stars: okay, average, fine
2 stars: disappointed, not good
1 star: terrible, awful, worst

Review: "{review[:200]}"

Return only JSON:
{{"predicted_stars": 4, "explanation": "reason"}}</s>
<|assistant|>"""
    
    result = pipe(prompt, max_new_tokens=100)
    return result[0]['generated_text'].split('<|assistant|>')[-1]


def prompt_cot_examples(review):
    prompt = f"""<|system|>
You are a rating classifier. Learn from examples then rate 1-5 stars and return only JSON.</s>
<|user|>
Examples:
"Food was incredible!" → 5 stars
"Good service" → 4 stars
"It was okay" → 3 stars
"Not impressed" → 2 stars
"Terrible" → 1 star

Review: "{review[:200]}"

Think: Is it very positive, positive, neutral, negative, or very negative?
Return only JSON:
{{"predicted_stars": 4, "explanation": "reason"}}</s>
<|assistant|>"""
    
    result = pipe(prompt, max_new_tokens=100)
    return result[0]['generated_text'].split('<|assistant|>')[-1]


def extract_json(text):
    try:
        text = str(text).strip()
        text = re.sub(r'```json\s*|\s*```', '', text)
        text = re.sub(r'<.*?>', '', text)
        text = text.strip()
        
        try:
            data = json.loads(text)
            if 'predicted_stars' in data:
                stars = int(data['predicted_stars'])
                if 1 <= stars <= 5:
                    data['predicted_stars'] = stars
                    return data
        except:
            pass
        
        match = re.search(r'\{[^{}]*"predicted_stars"[^{}]*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            stars = int(data['predicted_stars'])
            if 1 <= stars <= 5:
                return {"predicted_stars": stars, "explanation": data.get("explanation", "Extracted")}
        
        match = re.search(r'"predicted_stars"\s*:\s*(\d)', text)
        if match:
            stars = int(match.group(1))
            if 1 <= stars <= 5:
                return {"predicted_stars": stars, "explanation": "Extracted"}
        
        match = re.search(r'(\d)\s*stars?', text, re.IGNORECASE)
        if match:
            stars = int(match.group(1))
            if 1 <= stars <= 5:
                return {"predicted_stars": stars, "explanation": "Extracted"}
        
    except:
        pass
    
    return None


def test_approach(prompt_func, name):
    print(f"\nTesting: {name}")
    print("-" * 60)
    
    predictions = []
    explanations = []
    valid_json = 0
    failed = []
    
    for i, row in df_sample.iterrows():
        print(f"Processing {i+1}/200...", end='\r')
        
        try:
            response = prompt_func(row['text'])
            result = extract_json(response)
            
            if result:
                predictions.append(result['predicted_stars'])
                explanations.append(result.get('explanation', 'N/A'))
                valid_json += 1
            else:
                predictions.append(3)
                explanations.append('Parse failed')
                failed.append(i)
        except Exception as e:
            predictions.append(3)
            explanations.append(f'Error: {str(e)[:50]}')
            failed.append(i)
    
    correct = sum(1 for p, a in zip(predictions, df_sample['stars']) if int(p) == int(a))
    accuracy = correct / len(predictions) * 100
    mae = sum(abs(int(p) - int(a)) for p, a in zip(predictions, df_sample['stars'])) / len(predictions)
    json_rate = valid_json / len(predictions) * 100
    
    pred_dist = Counter(predictions)
    actual_dist = Counter(df_sample['stars'])
    
    print(f"\n")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"MAE: {mae:.2f}")
    print(f"Valid JSON: {json_rate:.1f}%")
    print(f"Failed: {len(failed)}")
    
    print(f"\nPredictions:")
    for s in sorted(pred_dist.keys()):
        print(f"  {s}★: {pred_dist[s]} ({pred_dist[s]/len(predictions)*100:.1f}%)")
    
    print(f"\nActual:")
    for s in sorted(actual_dist.keys()):
        print(f"  {s}★: {actual_dist[s]} ({actual_dist[s]/len(df_sample)*100:.1f}%)")
    
    return {
        'name': name,
        'accuracy': accuracy,
        'mae': mae,
        'json_rate': json_rate,
        'predictions': predictions,
        'explanations': explanations,
        'pred_dist': pred_dist,
        'failed': len(failed)
    }


print("=" * 60)
print("YELP RATING PREDICTION - LOCAL MODEL")
print("=" * 60)

r1 = test_approach(prompt_basic, "Approach 1: Basic")
r2 = test_approach(prompt_guided, "Approach 2: Keywords")
r3 = test_approach(prompt_cot_examples, "Approach 3: Examples + CoT")

print("\n" + "=" * 60)
print("RESULTS COMPARISON")
print("=" * 60)
print(f"{'Approach':<30} {'Accuracy':<12} {'MAE':<10} {'JSON Valid'}")
print("-" * 60)
print(f"{r1['name']:<30} {r1['accuracy']:>6.1f}%    {r1['mae']:>6.2f}    {r1['json_rate']:>6.1f}%")
print(f"{r2['name']:<30} {r2['accuracy']:>6.1f}%    {r2['mae']:>6.2f}    {r2['json_rate']:>6.1f}%")
print(f"{r3['name']:<30} {r3['accuracy']:>6.1f}%    {r3['mae']:>6.2f}    {r3['json_rate']:>6.1f}%")
print("=" * 60)

results = [r1, r2, r3]
best = max(results, key=lambda x: x['accuracy'])
print(f"\nBest Approach: {best['name']}")
print(f"  Accuracy: {best['accuracy']:.1f}%")
print(f"  MAE: {best['mae']:.2f}")
print(f"  JSON Success: {best['json_rate']:.1f}%")

df_out = pd.DataFrame({
    'review': df_sample['text'],
    'actual': df_sample['stars'],
    'basic_pred': r1['predictions'],
    'basic_expl': r1['explanations'],
    'keyword_pred': r2['predictions'],
    'keyword_expl': r2['explanations'],
    'cot_pred': r3['predictions'],
    'cot_expl': r3['explanations']
})
df_out.to_csv('predictions.csv', index=False)
print(f"\nResults saved to: predictions.csv")

print("\n" + "=" * 60)
print("DISCUSSION")
print("=" * 60)

print("\n1. PROMPT DESIGN RATIONALE:")
print("-" * 60)
print("""
Approach 1 (Basic Direct Prompt):
  Design: Simple, minimal prompt asking for star rating
  Purpose: Establish baseline - can model understand task without guidance?
  Expected: May struggle with edge cases and consistency

Approach 2 (Keyword-Guided Prompt):
  Design: Added sentiment keywords mapped to each rating level
  Why changed: Basic approach lacks explicit signals
  Expected improvement: More consistent classification using keyword hints

Approach 3 (Chain-of-Thought with Examples):
  Design: Few-shot examples + explicit reasoning step
  Why changed: Keywords alone may miss nuanced sentiment
  Expected improvement: Better handling of complex reviews through reasoning
""")

print("\n2. RESULTS ANALYSIS:")
print("-" * 60)

avg_json = sum(r['json_rate'] for r in results) / 3
print(f"Average JSON Success Rate: {avg_json:.1f}%")
if avg_json < 70:
    print("  ⚠️  Small model struggles with strict formatting")
else:
    print("  ✓ Model follows format reasonably well")

print(f"\nAccuracy Range: {min(r['accuracy'] for r in results):.1f}% - {max(r['accuracy'] for r in results):.1f}%")
improvement = best['accuracy'] - r1['accuracy']
print(f"Improvement over baseline: {improvement:+.1f}%")

if improvement > 5:
    print("  ✓ Significant improvement with prompt engineering")
elif improvement > 0:
    print("  ✓ Modest improvement with prompt engineering")
else:
    print("  ⚠️ No improvement - simpler prompt performs best")

print(f"\nMean Absolute Error:")
for r in results:
    print(f"  {r['name']}: {r['mae']:.2f}")

print("\n3. RELIABILITY & CONSISTENCY:")
print("-" * 60)

for r in results:
    most = r['pred_dist'].most_common(1)[0]
    print(f"\n{r['name']}:")
    print(f"  Most predicted: {most[0]}★ ({most[1]/len(r['predictions'])*100:.1f}%)")
    
    if most[0] == 3 and most[1] > 120:
        print(f"  ⚠️  Heavy bias toward neutral (3-star) rating")
    
    missing = set(range(1, 6)) - set(r['pred_dist'].keys())
    if missing:
        print(f"  ⚠️  Never predicted: {', '.join(str(x) for x in sorted(missing))}★")
    
    spread = max(r['pred_dist'].values()) - min(r['pred_dist'].values())
    if spread < 50:
        print(f"  ✓ Balanced distribution")

print("\n4. KEY FINDINGS:")
print("-" * 60)
print(f"""
Best Approach: {best['name']}
  - Accuracy: {best['accuracy']:.1f}%
  - MAE: {best['mae']:.2f}
  - JSON Success: {best['json_rate']:.1f}%

Key Success Factors:
  - {"Structured guidance with keywords" if "Keywords" in best['name'] else "Examples with reasoning" if "CoT" in best['name'] else "Simple, direct instructions"}
  
Challenges Observed:
  - Model size (1.1B) limits complex reasoning
  - Bias toward middle ratings (3-4 stars)
  - JSON formatting inconsistent
  - Underrepresents extreme ratings (1★ and 5★)

Recommendations:
  1. For better accuracy: Use larger model (7B+)
  2. For better JSON: Add more format examples
  3. For balanced predictions: Include edge case examples
  4. Consider ensemble voting across all three approaches
""")

print("\n" + "=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)
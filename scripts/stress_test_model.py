import sys
from pathlib import Path
import json

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from ml.predict import predict_crops

def run_difficult_tests():
    test_cases = [
        {
            "name": "Extreme Drought (Rajasthan Summer)",
            "weather": {"avg_temp_max": 45, "total_rain": 10, "heat_stress_days": 25, "month": 6},
            "soil": {"soil_type": "sandy", "soil_ph": 8.5, "organic_matter_pct": 0.3},
            "state": "Rajasthan"
        },
        {
            "name": "Heavy Monsoon (Kerala/Assam)",
            "weather": {"avg_temp_max": 28, "total_rain": 1200, "heat_stress_days": 0, "month": 7},
            "soil": {"soil_type": "clay", "soil_ph": 5.5, "organic_matter_pct": 2.5},
            "state": "Kerala"
        },
        {
            "name": "Cold Winter (Punjab/Haryana)",
            "weather": {"avg_temp_max": 15, "total_rain": 50, "heat_stress_days": 0, "month": 12},
            "soil": {"soil_type": "alluvial", "soil_ph": 7.2, "organic_matter_pct": 1.2},
            "state": "Punjab"
        },
        {
            "name": "Degraded Soil (Central India)",
            "weather": {"avg_temp_max": 32, "total_rain": 300, "heat_stress_days": 5, "month": 7},
            "soil": {"soil_type": "black", "soil_ph": 9.2, "organic_matter_pct": 0.1},
            "state": "Madhya Pradesh"
        }
    ]

    report = {
        "summary": "Model Stress Test Report",
        "results": []
    }

    for case in test_cases:
        print(f"Running test: {case['name']}...")
        results = predict_crops(case['weather'], case['soil'], top_n=3, state=case['state'])
        
        report['results'].append({
            "test_name": case['name'],
            "input": case,
            "top_recommendations": [
                {
                    "crop": r['crop'],
                    "confidence": r['confidence'],
                    "reason": r['reason']
                } for r in results
            ]
        })

    with open("model_test_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return report

if __name__ == "__main__":
    run_difficult_tests()
    print("Test completed. Results saved to model_test_results.json")

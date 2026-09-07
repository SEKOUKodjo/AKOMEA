import pandas as pd
from scipy import stats
import numpy as np

def detecter_anomalies(queryset):
    df = pd.DataFrame(list(queryset.values()))
    
    # Détecter les doublons
    doublons = df[df.duplicated(subset=['type_depense', 'quartier', 'prix', 'date'], keep=False)]
    
    # Détecter les valeurs aberrantes (méthode IQR)
    Q1 = df['prix'].quantile(0.25)
    Q3 = df['prix'].quantile(0.75)
    IQR = Q3 - Q1
    
    limite_inf = Q1 - 1.5 * IQR
    limite_sup = Q3 + 1.5 * IQR
    
    aberrants = df[(df['prix'] < limite_inf) | (df['prix'] > limite_sup)]
    
    return {
        'doublons': doublons,
        'aberrants': aberrants,
        'total_propre': len(df) - len(doublons) - len(aberrants)
    }
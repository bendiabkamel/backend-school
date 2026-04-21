CREATE TABLE IF NOT EXISTS paiements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID REFERENCES students(id) NOT NULL,
  formation_id UUID REFERENCES formations(id) NOT NULL,
  montant_du DECIMAL(10,2) NOT NULL,
  montant_verse DECIMAL(10,2) NOT NULL,
  mode_paiement VARCHAR(20) CHECK (mode_paiement IN ('especes','virement','cheque','ccp')),
  reference_recu VARCHAR(100),
  notes TEXT,
  date_paiement DATE NOT NULL DEFAULT CURRENT_DATE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paiements_student_id ON paiements(student_id);
CREATE INDEX IF NOT EXISTS idx_paiements_formation_id ON paiements(formation_id);
CREATE INDEX IF NOT EXISTS idx_paiements_date_paiement ON paiements(date_paiement);

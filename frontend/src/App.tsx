import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

interface Pagamento {
  [key: string]: string | number
  nome: string
}

interface ResumoData {
  pagamentos: Record<string, Pagamento>
  totais_semanas: Record<string, number>
  wednesdays: string[]
}

interface SummaryData {
  total_geral: number
  num_fornecedores: number
  totais_semanas: Record<string, number>
  wednesdays: string[]
}

function formatDate(date: Date): string {
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  return `${day}/${month}/${year}`
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(value)
}

function formatWeekLabel(index: number, wednesday: string): string {
  if (index === 0) return 'Vencido'
  const date = new Date(wednesday)
  return `Sem ${index} (${date.getDate()}/${String(date.getMonth() + 1).padStart(2, '0')})`
}

function getWeekColumns(wednesdays: string[]): Array<{ index: number; date: string }> {
  const columns: Array<{ index: number; date: string }> = [{ index: 0, date: '' }]

  for (let i = 0; i < Math.min(wednesdays.length, 12); i++) {
    columns.push({ index: i + 1, date: wednesdays[i] })
  }

  return columns
}

function App() {
  const [pagamentos, setPagamentos] = useState<Record<string, Pagamento>>({})
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [weekColumns, setWeekColumns] = useState<Array<{ index: number; date: string }>>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get<ResumoData>('/api/pagamentos')
        setPagamentos(response.data.pagamentos)

        const columns = getWeekColumns(response.data.wednesdays)
        setWeekColumns(columns)

        const summaryResponse = await axios.get<SummaryData>('/api/resumo')
        setSummary(summaryResponse.data)
      } catch (error) {
        console.error('Erro ao buscar dados:', error)
      }
    }

    fetchData()
  }, [])

  const sortedFornecedores = Object.entries(pagamentos)
    .sort((a, b) => {
      const numA = parseInt(a[0].slice(-4), 10)
      const numB = parseInt(b[0].slice(-4), 10)
      return numA - numB
    })

  return (
    <div className="pagamentos-container">
      <header className="pagamentos-header">
        <h1>Planeamento de Pagamentos - Documentos a pagar por semana em: {formatDate(new Date())}</h1>
      </header>

      {summary && (
        <div className="summary-cards">
          <div className="summary-card">
            <div className="card-value">{formatCurrency(summary.total_geral)}</div>
            <div className="card-label">Total a Pagar</div>
          </div>
          <div className="summary-card">
            <div className="card-value">{summary.num_fornecedores}</div>
            <div className="card-label">Fornecedores</div>
          </div>
        </div>
      )}

      <div className="table-container">
        <table className="pagamentos-table">
          <thead>
            <tr>
              <th className="col-forn">Forn. Nº</th>
              <th className="col-nome">Fornecedor</th>
              {weekColumns.map((col) => (
                <th key={col.index} className="col-semana">
                  {formatWeekLabel(col.index, col.date)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedFornecedores.map(([codigo, dados]) => (
              <tr key={codigo}>
                <td className="col-forn"><strong>{codigo.slice(-4)}</strong></td>
                <td className="col-nome">{dados.nome}</td>
                {weekColumns.map((col) => {
                  const chaveWeek = `semana_${col.index}`
                  const valor = (dados[chaveWeek] as number) || 0
                  return (
                    <td key={col.index} className="col-semana text-right">
                      {valor > 0 ? formatCurrency(valor) : '-'}
                    </td>
                  )
                })}
              </tr>
            ))}
            <tr className="totals-row">
              <td colSpan={2} className="col-total"><strong>TOTAL</strong></td>
              {weekColumns.map((col) => {
                const chaveWeek = `semana_${col.index}`
                const total = summary?.totais_semanas[chaveWeek] || 0
                return (
                  <td key={col.index} className="col-semana text-right">
                    <strong>{total > 0 ? formatCurrency(total) : '-'}</strong>
                  </td>
                )
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default App

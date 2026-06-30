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
  semanas: string[]
  total_vencido: number
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

function formatWeekLabel(weekKey: string): JSX.Element {
  const parts = weekKey.replace('semana_', '').split('_')
  const weekNumber = parseInt(parts[0], 10)
  const year = parseInt(parts[1], 10)
  return (
    <>
      Semana<br/>{weekNumber}/{year}
    </>
  )
}

function getWeekColumns(semanas: string[]): string[] {
  return semanas
}

function App() {
  const [pagamentos, setPagamentos] = useState<Record<string, Pagamento>>({})
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [weekColumns, setWeekColumns] = useState<string[]>([])
  const [totalVencido, setTotalVencido] = useState<number>(0)
  const [cheques, setCheques] = useState<any[]>([])
  const [totalCheques, setTotalCheques] = useState<number>(0)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get<ResumoData>('/api/pagamentos')
        setPagamentos(response.data.pagamentos)

        const columns = getWeekColumns(response.data.semanas)
        setWeekColumns(columns)

        // Total vencido calculado no backend (faturas com data de vencimento <= hoje)
        setTotalVencido(response.data.total_vencido || 0)

        const summaryResponse = await axios.get<SummaryData>('/api/resumo')
        setSummary(summaryResponse.data)

        // Buscar cheques pré-datados
        const chequesResponse = await axios.get('/api/cheques-predatados')
        setCheques(chequesResponse.data.cheques)
        setTotalCheques(chequesResponse.data.total_geral || 0)
      } catch (error) {
        console.error('Erro ao buscar dados:', error)
      }
    }

    fetchData()
  }, [])

  const codigosDebitoDirecto = ['0243', '0303', '0308', '1009', '1028', '1035', '1114']

  const sortedFornecedores = Object.entries(pagamentos)
    .sort((a, b) => {
      const numA = parseInt(a[0].slice(-4), 10)
      const numB = parseInt(b[0].slice(-4), 10)
      return numA - numB
    })

  const fornecedoresTransferenciaComDivida = sortedFornecedores.filter(
    ([codigo, dados]) =>
      !codigosDebitoDirecto.includes(codigo.slice(-4)) &&
      (dados.total_divida as number) >= 0
  )

  const fornecedoresTransferenciaComCredito = sortedFornecedores.filter(
    ([codigo, dados]) =>
      !codigosDebitoDirecto.includes(codigo.slice(-4)) &&
      (dados.total_divida as number) < 0
  )

  const fornecedoresDebito = sortedFornecedores.filter(
    ([codigo]) => codigosDebitoDirecto.includes(codigo.slice(-4))
  )

  const renderTable = (fornecedores: typeof sortedFornecedores, titulo: string) => (
    <>
      <div className="table-title">{titulo}</div>
      <table className="pagamentos-table">
        <thead>
          <tr>
            <th className="col-forn">Forn. Nº</th>
            <th className="col-nome">Fornecedor</th>
            {weekColumns.map((col) => (
              <th key={col} className="col-semana">
                {formatWeekLabel(col)}
              </th>
            ))}
            <th className="col-total">Total em Dívida</th>
          </tr>
        </thead>
        <tbody>
          {fornecedores.map(([codigo, dados]) => (
            <tr key={codigo}>
              <td className="col-forn"><strong>{codigo.slice(-4)}</strong></td>
              <td className="col-nome">{dados.nome}</td>
              {weekColumns.map((col) => {
                const valor = (dados[col] as number) || 0
                return (
                  <td key={col} className="col-semana text-right">
                    {valor > 0 ? formatCurrency(valor) : '-'}
                  </td>
                )
              })}
              <td className="col-total text-right">
                <strong>{formatCurrency((dados.total_divida as number) || 0)}</strong>
              </td>
            </tr>
          ))}
          <tr className="totals-row">
            <td colSpan={2} className="col-total"><strong>TOTAL</strong></td>
            {weekColumns.map((col) => {
              const total = fornecedores.reduce((acc, [codigo]) => {
                const valor = (pagamentos[codigo]?.[col] as number) || 0
                return acc + valor
              }, 0)
              return (
                <td key={col} className="col-semana text-right">
                  <strong>{total > 0 ? formatCurrency(total) : '-'}</strong>
                </td>
              )
            })}
            <td className="col-total text-right">
              <strong>
                {formatCurrency(
                  fornecedores.reduce((acc, [codigo]) => acc + ((pagamentos[codigo]?.total_divida as number) || 0), 0)
                )}
              </strong>
            </td>
          </tr>
        </tbody>
      </table>
    </>
  )

  const renderChequesTable = () => (
    <>
      <div className="table-title">FORNECEDORES - CHEQUES PRÉ-DATADOS</div>
      <table className="pagamentos-table">
        <thead>
          <tr>
            <th className="col-forn">Forn. Nº</th>
            <th className="col-nome">Cheque Pré-datado Nº - Entidade Sacada</th>
            <th className="col-semana">Data Vencimento</th>
            <th className="col-total">Valor</th>
          </tr>
        </thead>
        <tbody>
          {cheques.map((cheque, idx) => (
            <tr key={idx}>
              <td className="col-forn"><strong>{cheque.codigo_entidade}</strong></td>
              <td className="col-nome">{cheque.numero_documento} {cheque.entidade_sacada}</td>
              <td className="col-semana">{formatDate(new Date(cheque.data_emissao))}</td>
              <td className="col-total text-right">
                <strong>{formatCurrency(cheque.valor)}</strong>
              </td>
            </tr>
          ))}
          <tr className="totals-row">
            <td colSpan={3} className="col-total"><strong>TOTAL</strong></td>
            <td className="col-total text-right">
              <strong>{formatCurrency(totalCheques)}</strong>
            </td>
          </tr>
        </tbody>
      </table>
    </>
  )

  return (
    <div className="pagamentos-container">
      <header className="pagamentos-header">
        <h1>
          CLÁSSICO DESPORTIVO - Planeamento de Pagamentos - Documentos a pagar por semana em: {formatDate(new Date())}
          <span className="header-total-vencido">Total Vencido: {formatCurrency(totalVencido)}</span>
        </h1>
        {summary && (
          <div className="header-total">
            <span className="header-total-label">Total a Pagar:</span>
            <span className="header-total-value">{formatCurrency(summary.total_geral)}</span>
          </div>
        )}
      </header>


      <div className="table-container">
        {renderTable(fornecedoresTransferenciaComDivida, 'FORNECEDORES - TRANSFERÊNCIA BANCÁRIA')}
        {renderTable(fornecedoresDebito, 'FORNECEDORES - DÉBITO DIRECTO')}
        {renderTable(fornecedoresTransferenciaComCredito, 'FORNECEDORES - COM CRÉDITOS')}
        {cheques.length > 0 && renderChequesTable()}
      </div>
    </div>
  )
}

export default App

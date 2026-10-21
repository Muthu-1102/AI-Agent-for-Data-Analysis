import pytest
import pandas as pd
from unittest.mock import patch, AsyncMock, MagicMock
import subprocess

from agents.schema_agent import SchemaAgent
from agents.prompt_agent import PromptAgent
from agents.code_agent import CodeAgent
from agents.validation_agent import ValidationAgent
from agents.execution_agent import ExecutionAgent
from agents.report_agent import ReportAgent
from utils.helpers import resolve_dataset_path


@pytest.mark.asyncio
async def test_schema_agent_success(mocker):
    agent = SchemaAgent()
    mock_df = pd.DataFrame({
        'name': ['Alice', 'Bob'],
        'age': [25, 30],
        'score': [85.5, 92.0]
    })
    mocker.patch('pandas.read_csv', return_value=mock_df)
    mocker.patch('agents.schema_agent.resolve_dataset_path', return_value='dummy.csv')
    
    state = {'file_id': 'test.csv'}
    result = await agent.process(state)
    
    schema_info = result['schema_info']
    assert schema_info['columns'] == ['name', 'age', 'score']
    assert schema_info['row_count'] == 2
    assert len(schema_info['column_details']) == 3
    assert schema_info['column_details'][0]['name'] == 'name'
    assert schema_info['column_details'][0]['dtype'] == 'object'


@pytest.mark.asyncio
async def test_schema_agent_file_not_found(mocker):
    agent = SchemaAgent()
    mocker.patch('agents.schema_agent.resolve_dataset_path', side_effect=FileNotFoundError('Not found'))
    
    state = {'file_id': 'missing.csv'}
    with pytest.raises(RuntimeError, match="Data file could not be found"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_prompt_agent_success():
    agent = PromptAgent()
    state = {
        'query': 'What is the average age?',
        'schema_info': {
            'columns': ['name', 'age'],
            'dtypes': {'name': 'object', 'age': 'int64'},
            'null_counts': {'name': 0, 'age': 0},
            'row_count': 100,
            'sample_rows': []
        }
    }
    result = await agent.process(state)
    
    assert 'structured_prompt' in result
    assert 'What is the average age?' in result['structured_prompt']


@pytest.mark.asyncio
async def test_code_agent_success(mocker):
    agent = CodeAgent()
    mock_llm = mocker.patch.object(agent.llm_service, 'generate_response', new_callable=AsyncMock)
    mock_llm.return_value = "print(df['age'].mean())"
    
    state = {
        'structured_prompt': 'Generate code to calculate average age',
        'schema_info': {
            'columns': ['age'],
            'dtypes': {'age': 'int64'},
            'null_counts': {'age': 0},
            'row_count': 10
        }
    }
    result = await agent.process(state)
    
    assert result['generated_code'] == "print(df['age'].mean())"
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_validation_agent_safe_code():
    agent = ValidationAgent()
    safe_code = "print(df['age'].mean())"
    state = {'generated_code': safe_code}
    result = await agent.process(state)
    
    assert result['validation_passed'] is True


@pytest.mark.asyncio
async def test_validation_agent_unsafe_import():
    agent = ValidationAgent()
    unsafe_code = "import os\nprint('hello')"
    state = {'generated_code': unsafe_code}
    with pytest.raises(PermissionError, match="Unsafe import blocked"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_validation_agent_unsafe_builtin():
    agent = ValidationAgent()
    unsafe_code = "eval('1+1')"
    state = {'generated_code': unsafe_code}
    with pytest.raises(PermissionError, match="Unsafe built-in function blocked"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_validation_agent_dunder_blocked():
    agent = ValidationAgent()
    unsafe_code = "x = df.__class__.__subclasses__()"
    state = {'generated_code': unsafe_code}
    with pytest.raises(PermissionError, match="Unsafe dunder attribute access blocked"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_validation_agent_disk_write_blocked():
    agent = ValidationAgent()
    unsafe_code = "df.to_csv('leak.csv')"
    state = {'generated_code': unsafe_code}
    with pytest.raises(PermissionError, match="Unsafe file write or serialization method blocked"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_execution_agent_success(mocker):
    agent = ExecutionAgent()
    mocker.patch('agents.execution_agent.resolve_dataset_path', return_value='dummy.csv')
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '27.5\n'
    mock_proc.stderr = ''
    mocker.patch('subprocess.run', return_value=mock_proc)
    
    safe_code = "result = df['age'].mean()\nprint(result)"
    state = {'generated_code': safe_code, 'file_id': 'test.csv'}
    result = await agent.process(state)
    
    assert result['execution_success'] is True
    assert '27.5' in result['captured_output']


@pytest.mark.asyncio
async def test_execution_agent_unsafe_code(mocker):
    agent = ExecutionAgent()
    mocker.patch('agents.execution_agent.resolve_dataset_path', return_value='dummy.csv')
    mocker.patch('agents.execution_agent.Sandbox.is_safe_code', return_value=False)
    
    state = {'generated_code': 'import os', 'file_id': 'test.csv'}
    with pytest.raises(PermissionError, match="Execution blocked"):
        await agent.process(state)


@pytest.mark.asyncio
async def test_report_agent_success(mocker):
    agent = ReportAgent()
    mock_llm = mocker.patch.object(agent.llm_service, 'generate_response', new_callable=AsyncMock)
    mock_llm.return_value = "The average age is 27.5"
    
    state = {
        'execution_success': True,
        'captured_output': '27.5',
        'query': 'What is the average age?'
    }
    result = await agent.process(state)
    
    assert result['insights_summary'] == "The average age is 27.5"
    assert result['report_generated'] is True


@pytest.mark.asyncio
async def test_report_agent_execution_failure():
    agent = ReportAgent()
    state = {
        'execution_success': False,
        'error_trace': 'Some error',
        'query': 'What is the average?'
    }
    result = await agent.process(state)
    
    assert 'unavailable' in result['insights_summary'].lower() or 'error' in result['insights_summary'].lower()
    assert result['report_generated'] is True


def test_path_traversal_blocked():
    with pytest.raises(ValueError, match="Directory traversal"):
        resolve_dataset_path("../../etc/passwd")
    
    with pytest.raises(ValueError, match="Directory traversal"):
        resolve_dataset_path("..\\windows\\win.ini")

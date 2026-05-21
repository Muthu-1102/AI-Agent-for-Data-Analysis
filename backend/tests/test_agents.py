import pytest
import pandas as pd
from unittest.mock import patch, AsyncMock

from agents.schema_agent import SchemaAgent
from agents.prompt_agent import PromptAgent
from agents.code_agent import CodeAgent
from agents.validation_agent import ValidationAgent
from agents.execution_agent import ExecutionAgent
from agents.report_agent import ReportAgent


@pytest.mark.asyncio
async def test_schema_agent_success(mocker):
    agent = SchemaAgent()
    mock_df = pd.DataFrame({
        'name': ['Alice', 'Bob'],
        'age': [25, 30],
        'score': [85.5, 92.0]
    })
    mocker.patch('pandas.read_csv', return_value=mock_df)
    mocker.patch('backend.utils.helpers.resolve_dataset_path', return_value='dummy.csv')
    
    state = {'file_id': 'test.csv'}
    result = await agent.process(state)
    
    assert result['columns'] == ['name', 'age', 'score']
    assert result['row_count'] == 2
    assert len(result['column_details']) == 3
    assert result['column_details'][0]['name'] == 'name'
    assert result['column_details'][0]['dtype'] == 'object'


@pytest.mark.asyncio
async def test_schema_agent_file_not_found(mocker):
    agent = SchemaAgent()
    mocker.patch('pandas.read_csv', side_effect=FileNotFoundError('Not found'))
    mocker.patch('backend.utils.helpers.resolve_dataset_path', return_value='nonexistent.csv')
    
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
            'row_count': 100
        }
    }
    result = await agent.process(state)
    
    assert 'prompt_plan' in result
    assert 'What is the average age?' in result['prompt_plan']


@pytest.mark.asyncio
async def test_code_agent_success(mocker):
    agent = CodeAgent()
    mock_llm = mocker.patch.object(agent.llm_service, 'generate_response', new_callable=AsyncMock)
    mock_llm.return_value = "print(df['age'].mean())"
    
    state = {
        'prompt_plan': 'Generate code to calculate average age',
        'schema_info': {'columns': ['age']}
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
async def test_execution_agent_success(mocker):
    agent = ExecutionAgent()
    mock_df = pd.DataFrame({'age': [25, 30]})
    mocker.patch('pandas.read_csv', return_value=mock_df)
    mocker.patch('backend.utils.helpers.resolve_dataset_path', return_value='dummy.csv')
    mocker.patch('backend.utils.sandbox.Sandbox.is_safe_code', return_value=True)
    
    safe_code = "result = df['age'].mean()\nprint(result)"
    state = {'generated_code': safe_code, 'file_id': 'test.csv'}
    result = await agent.process(state)
    
    assert result['execution_success'] is True
    assert '27.5' in result['captured_output']


@pytest.mark.asyncio
async def test_execution_agent_unsafe_code(mocker):
    agent = ExecutionAgent()
    mocker.patch('backend.utils.sandbox.Sandbox.is_safe_code', return_value=False)
    
    state = {'generated_code': 'import os', 'file_id': 'test.csv'}
    with pytest.raises(RuntimeError, match="Execution blocked"):
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
    
    assert 'encountered an error' in result['insights_summary']
    assert result['report_generated'] is True

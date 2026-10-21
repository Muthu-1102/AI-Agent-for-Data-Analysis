import pytest
from unittest.mock import AsyncMock, patch

from core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_success(mocker):
    orchestrator = Orchestrator()
    
    # Mock all agents
    mock_schema = mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock)
    mock_schema.return_value = {'schema_info': {'columns': ['age'], 'dtypes': {'age': 'int64'}, 'null_counts': {'age': 0}, 'row_count': 10, 'sample_rows': []}}
    
    mock_prompt = mocker.patch.object(orchestrator.prompt_agent, 'process', new_callable=AsyncMock)
    mock_prompt.return_value = {'structured_prompt': 'Calculate average age'}
    
    mock_code = mocker.patch.object(orchestrator.code_agent, 'process', new_callable=AsyncMock)
    mock_code.return_value = {'generated_code': 'print(df["age"].mean())'}
    
    mock_validation = mocker.patch.object(orchestrator.validation_agent, 'process', new_callable=AsyncMock)
    mock_validation.return_value = {'validation_passed': True}
    
    mock_execution = mocker.patch.object(orchestrator.execution_agent, 'process', new_callable=AsyncMock)
    mock_execution.return_value = {'execution_success': True, 'captured_output': '25.0'}
    
    mock_report = mocker.patch.object(orchestrator.report_agent, 'process', new_callable=AsyncMock)
    mock_report.return_value = {'insights_summary': 'The average age is 25.0'}
    
    result = await orchestrator.execute_pipeline('Test query', 'test.csv')
    
    assert result['status'] == 'completed'
    assert result['execution_success'] is True
    assert result['insights_summary'] == 'The average age is 25.0'
    assert result['captured_output'] == '25.0'
    
    # Check that all agents were called
    mock_schema.assert_called_once()
    mock_prompt.assert_called_once()
    mock_code.assert_called_once()
    mock_validation.assert_called_once()
    mock_execution.assert_called_once()
    mock_report.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_validation_failure_exhausts_retries(mocker):
    orchestrator = Orchestrator()
    
    # Mock schema & prompt
    mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock, return_value={'schema_info': {'columns': ['age'], 'dtypes': {'age': 'int64'}, 'null_counts': {'age': 0}, 'row_count': 10, 'sample_rows': []}})
    mocker.patch.object(orchestrator.prompt_agent, 'process', new_callable=AsyncMock, return_value={'structured_prompt': 'prompt'})
    mock_code = mocker.patch.object(orchestrator.code_agent, 'process', new_callable=AsyncMock, return_value={'generated_code': 'import os'})
    
    # Validation fails on all attempts
    mock_validation = mocker.patch.object(orchestrator.validation_agent, 'process', new_callable=AsyncMock)
    mock_validation.side_effect = PermissionError('Forbidden import: os')
    
    mock_report = mocker.patch.object(orchestrator.report_agent, 'process', new_callable=AsyncMock, return_value={'insights_summary': 'Execution failed'})
    
    result = await orchestrator.execute_pipeline('Test query', 'test.csv')
    
    assert result['status'] == 'failed'
    assert result['execution_success'] is False
    assert 'Forbidden import: os' in result['error']
    # CodeAgent was retried 3 times
    assert mock_code.call_count == 3


@pytest.mark.asyncio
async def test_orchestrator_self_repair_recovers(mocker):
    orchestrator = Orchestrator()
    
    mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock, return_value={'schema_info': {'columns': ['age'], 'dtypes': {'age': 'int64'}, 'null_counts': {'age': 0}, 'row_count': 10, 'sample_rows': []}})
    mocker.patch.object(orchestrator.prompt_agent, 'process', new_callable=AsyncMock, return_value={'structured_prompt': 'prompt'})
    
    # CodeAgent produces bad code first, good code second
    mock_code = mocker.patch.object(orchestrator.code_agent, 'process', new_callable=AsyncMock)
    mock_code.side_effect = [
        {'generated_code': 'import os'},
        {'generated_code': 'print(df["age"].mean())'}
    ]
    
    # ValidationAgent rejects first, approves second
    mock_validation = mocker.patch.object(orchestrator.validation_agent, 'process', new_callable=AsyncMock)
    mock_validation.side_effect = [
        PermissionError('Forbidden import: os'),
        {'validation_passed': True}
    ]
    
    mocker.patch.object(orchestrator.execution_agent, 'process', new_callable=AsyncMock, return_value={'execution_success': True, 'captured_output': '25.0'})
    mocker.patch.object(orchestrator.report_agent, 'process', new_callable=AsyncMock, return_value={'insights_summary': 'Average age is 25.0'})
    
    result = await orchestrator.execute_pipeline('Test query', 'test.csv')
    
    assert result['status'] == 'completed'
    assert result['execution_success'] is True
    assert mock_code.call_count == 2
    assert mock_validation.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_schema_failure_handled(mocker):
    orchestrator = Orchestrator()
    mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock, side_effect=RuntimeError('Data file could not be found: missing.csv'))
    
    result = await orchestrator.execute_pipeline('Test query', 'missing.csv')
    
    assert result['status'] == 'error'
    assert 'missing.csv' in result['error']

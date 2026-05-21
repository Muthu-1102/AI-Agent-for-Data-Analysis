import pytest
from unittest.mock import AsyncMock, patch

from core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_success(mocker):
    orchestrator = Orchestrator()
    
    # Mock all agents
    mock_schema = mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock)
    mock_schema.return_value = {'schema_info': 'mocked'}
    
    mock_prompt = mocker.patch.object(orchestrator.prompt_agent, 'process', new_callable=AsyncMock)
    mock_prompt.return_value = {'prompt_plan': 'mocked'}
    
    mock_code = mocker.patch.object(orchestrator.code_agent, 'process', new_callable=AsyncMock)
    mock_code.return_value = {'generated_code': 'print("hello")'}
    
    mock_validation = mocker.patch.object(orchestrator.validation_agent, 'process', new_callable=AsyncMock)
    mock_validation.return_value = {'validation_passed': True}
    
    mock_execution = mocker.patch.object(orchestrator.execution_agent, 'process', new_callable=AsyncMock)
    mock_execution.return_value = {'execution_success': True, 'captured_output': 'hello'}
    
    mock_report = mocker.patch.object(orchestrator.report_agent, 'process', new_callable=AsyncMock)
    mock_report.return_value = {'insights_summary': 'Mocked summary'}
    
    result = await orchestrator.execute_pipeline('Test query', 'test.csv')
    
    assert result['query'] == 'Test query'
    assert result['file_id'] == 'test.csv'
    assert result['insights_summary'] == 'Mocked summary'
    
    # Check that all agents were called
    mock_schema.assert_called_once()
    mock_prompt.assert_called_once()
    mock_code.assert_called_once()
    mock_validation.assert_called_once()
    mock_execution.assert_called_once()
    mock_report.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_validation_failure(mocker):
    orchestrator = Orchestrator()
    
    # Mock agents up to validation
    mocker.patch.object(orchestrator.schema_agent, 'process', new_callable=AsyncMock, return_value={'schema_info': 'mocked'})
    mocker.patch.object(orchestrator.prompt_agent, 'process', new_callable=AsyncMock, return_value={'prompt_plan': 'mocked'})
    mocker.patch.object(orchestrator.code_agent, 'process', new_callable=AsyncMock, return_value={'generated_code': 'unsafe code'})
    
    # Validation fails
    mock_validation = mocker.patch.object(orchestrator.validation_agent, 'process', new_callable=AsyncMock)
    mock_validation.side_effect = PermissionError('Validation failed')
    
    with pytest.raises(PermissionError):
        await orchestrator.execute_pipeline('Test query', 'test.csv')

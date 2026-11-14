namespace Shop.Application.Features.Orders;

/// <summary>What the checked state write did.</summary>
public enum OrderStateOutcome
{
    Set,
    NotFound,
    NotAllowed,
}
